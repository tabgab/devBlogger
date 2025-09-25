#!/usr/bin/env python3
"""
DevBlogger - GitHub API client
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import (
    GitHubUser, GitHubRepository, GitHubCommit, GitHubBranch,
    GitHubRateLimit, GitHubError
)
from .auth import GitHubAuth
from ..config.settings import Settings


class GitHubClient:
    """GitHub API client with authentication and rate limiting."""

    def __init__(self, auth: GitHubAuth, settings: Settings):
        """Initialize GitHub API client."""
        self.auth = auth
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # API configuration
        self.base_url = self.settings.get("github.api_base_url", "https://api.github.com")
        self.api_version = "2022-11-28"  # GitHub API version
        self.timeout = 30
        self.max_retries = 3

        # Rate limiting
        self.rate_limit = None
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Minimum 100ms between requests

        # Session with retry strategy
        self._setup_session()

    def _setup_session(self):
        """Set up requests session with retry strategy."""
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            'Accept': f'application/vnd.github.v3+json',
            'User-Agent': 'DevBlogger/1.0',
            'X-GitHub-Api-Version': self.api_version
        })

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        if self.auth.is_authenticated():
            headers['Authorization'] = f'Bearer {self.auth.get_access_token()}'
        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """Make HTTP request to GitHub API with rate limiting."""
        # Respect rate limits
        self._wait_for_rate_limit()

        # Build URL
        url = urljoin(self.base_url, endpoint.lstrip('/'))

        # Prepare request
        headers = self._get_auth_headers()

        try:
            self.logger.debug(f"Making {method} request to {url}")

            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=self.timeout
            )

            # Update rate limit info
            if 'x-ratelimit-limit' in response.headers:
                self.rate_limit = GitHubRateLimit.from_headers(dict(response.headers))

            # Log rate limit status
            if self.rate_limit:
                self.logger.debug(
                    f"Rate limit: {self.rate_limit.remaining}/{self.rate_limit.limit} "
                    f"(resets at {self.rate_limit.reset})"
                )

            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise

    def _wait_for_rate_limit(self):
        """Wait if we're approaching rate limits."""
        if not self.rate_limit:
            return

        # If we're getting close to the limit, wait
        if self.rate_limit.remaining < 10:
            wait_time = (self.rate_limit.reset - time.time()) + 1
            if wait_time > 0:
                self.logger.info(f"Rate limit low, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)

        # Ensure minimum interval between requests
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        self.last_request_time = time.time()

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and convert to appropriate format."""
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error = GitHubError.from_api_response(error_data)
                self.logger.error(f"GitHub API error: {error.message}")
                raise ValueError(f"GitHub API error: {error.message}")
            except (ValueError, KeyError):
                response.raise_for_status()

        try:
            return response.json()
        except ValueError:
            return {}

    def get_authenticated_user(self) -> GitHubUser:
        """Get the authenticated user's information."""
        if not self.auth.is_authenticated():
            raise ValueError("User is not authenticated")

        response = self._make_request('GET', '/user')
        user_data = self._handle_response(response)
        return GitHubUser.from_api_response(user_data)

    def get_user_repositories(
        self,
        username: Optional[str] = None,
        include_private: bool = False,
        per_page: int = 30,
        page: int = 1
    ) -> List[GitHubRepository]:
        """Get repositories for a user."""
        if not self.auth.is_authenticated():
            raise ValueError("User is not authenticated")

        # Use authenticated user if no username specified
        if username is None:
            user = self.get_authenticated_user()
            username = user.login

        params = {
            'per_page': min(per_page, 100),
            'page': page,
            'type': 'owner' if not include_private else 'all'
        }

        endpoint = f'/users/{username}/repos'
        response = self._make_request('GET', endpoint, params=params)
        repos_data = self._handle_response(response)

        repositories = []
        for repo_data in repos_data:
            try:
                repo = GitHubRepository.from_api_response(repo_data)
                repositories.append(repo)
            except Exception as e:
                self.logger.warning(f"Failed to parse repository data: {e}")

        return repositories

    def get_repository(self, owner: str, repo: str) -> GitHubRepository:
        """Get detailed information about a specific repository."""
        endpoint = f'/repos/{owner}/{repo}'
        response = self._make_request('GET', endpoint)
        repo_data = self._handle_response(response)
        return GitHubRepository.from_api_response(repo_data)

    def get_repository_commits(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        per_page: int = 30,
        page: int = 1
    ) -> List[GitHubCommit]:
        """Get commits for a repository."""
        params = {
            'per_page': min(per_page, 100),
            'page': page
        }

        if branch:
            params['sha'] = branch
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        if author:
            params['author'] = author

        endpoint = f'/repos/{owner}/{repo}/commits'
        response = self._make_request('GET', endpoint, params=params)
        commits_data = self._handle_response(response)

        commits = []
        for commit_data in commits_data:
            try:
                commit = GitHubCommit.from_api_response(commit_data)
                commits.append(commit)
            except Exception as e:
                self.logger.warning(f"Failed to parse commit data: {e}")

        return commits

    def get_commit_details(self, owner: str, repo: str, commit_sha: str) -> GitHubCommit:
        """Get detailed information about a specific commit."""
        endpoint = f'/repos/{owner}/{repo}/commits/{commit_sha}'
        response = self._make_request('GET', endpoint)
        commit_data = self._handle_response(response)
        return GitHubCommit.from_api_response(commit_data)

    def get_commit_diff(self, owner: str, repo: str, commit_sha: str) -> str:
        """Get the diff for a specific commit."""
        endpoint = f'/repos/{owner}/{repo}/commits/{commit_sha}'
        response = self._make_request('GET', endpoint)
        commit_data = self._handle_response(response)

        # Extract diff from the files data
        diff = ""
        for file_data in commit_data.get('files', []):
            if file_data.get('patch'):
                diff += file_data['patch'] + '\n'

        return diff

    def get_repository_branches(self, owner: str, repo: str) -> List[GitHubBranch]:
        """Get all branches for a repository."""
        endpoint = f'/repos/{owner}/{repo}/branches'
        response = self._make_request('GET', endpoint)
        branches_data = self._handle_response(response)

        branches = []
        for branch_data in branches_data:
            try:
                branch = GitHubBranch.from_api_response(branch_data)
                branches.append(branch)
            except Exception as e:
                self.logger.warning(f"Failed to parse branch data: {e}")

        return branches

    def get_repository_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Get programming languages used in a repository."""
        endpoint = f'/repos/{owner}/{repo}/languages'
        response = self._make_request('GET', endpoint)
        languages_data = self._handle_response(response)
        return languages_data

    def search_repositories(
        self,
        query: str,
        sort: str = 'updated',
        order: str = 'desc',
        per_page: int = 30,
        page: int = 1
    ) -> List[GitHubRepository]:
        """Search for repositories."""
        params = {
            'q': query,
            'sort': sort,
            'order': order,
            'per_page': min(per_page, 100),
            'page': page
        }

        endpoint = '/search/repositories'
        response = self._make_request('GET', endpoint, params=params)
        search_data = self._handle_response(response)

        repositories = []
        for repo_data in search_data.get('items', []):
            try:
                repo = GitHubRepository.from_api_response(repo_data)
                repositories.append(repo)
            except Exception as e:
                self.logger.warning(f"Failed to parse repository data: {e}")

        return repositories

    def get_rate_limit_status(self) -> GitHubRateLimit:
        """Get current rate limit status."""
        endpoint = '/rate_limit'
        response = self._make_request('GET', endpoint)
        rate_data = self._handle_response(response)

        # Extract core rate limit (not search)
        core_limit = rate_data.get('rate', {})
        return GitHubRateLimit(
            limit=core_limit.get('limit', 0),
            remaining=core_limit.get('remaining', 0),
            reset=time.time() + core_limit.get('reset', 0),
            used=core_limit.get('limit', 0) - core_limit.get('remaining', 0),
            resource='core'
        )

    def test_connection(self) -> bool:
        """Test connection to GitHub API."""
        try:
            # Try to get rate limit status (doesn't require authentication)
            self.get_rate_limit_status()
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if client has valid authentication."""
        return self.auth.is_authenticated()

    def get_remaining_requests(self) -> int:
        """Get remaining API requests for this hour."""
        if self.rate_limit:
            return self.rate_limit.remaining
        return 0

    def close(self):
        """Close the HTTP session."""
        if hasattr(self, 'session'):
            self.session.close()
