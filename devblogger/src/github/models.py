#!/usr/bin/env python3
"""
DevBlogger - GitHub data models
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class GitHubUser:
    """GitHub user model."""
    login: str
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    blog: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    following: int = 0

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'GitHubUser':
        """Create GitHubUser from GitHub API response."""
        return cls(
            login=data.get('login', ''),
            id=data.get('id', 0),
            name=data.get('name'),
            email=data.get('email'),
            avatar_url=data.get('avatar_url'),
            bio=data.get('bio'),
            company=data.get('company'),
            location=data.get('location'),
            blog=data.get('blog'),
            public_repos=data.get('public_repos', 0),
            followers=data.get('followers', 0),
            following=data.get('following', 0)
        )


@dataclass
class GitHubRepository:
    """GitHub repository model."""
    id: int
    name: str
    full_name: str
    owner: GitHubUser
    description: Optional[str] = None
    private: bool = False
    html_url: str = ""
    clone_url: str = ""
    ssh_url: str = ""
    language: Optional[str] = None
    languages: Dict[str, int] = None
    default_branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    size: int = 0
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    watchers: int = 0
    archived: bool = False
    disabled: bool = False
    license: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'GitHubRepository':
        """Create GitHubRepository from GitHub API response."""
        owner_data = data.get('owner', {})
        owner = GitHubUser.from_api_response(owner_data)

        # Parse datetime fields
        created_at = None
        updated_at = None
        pushed_at = None

        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        if data.get('pushed_at'):
            pushed_at = datetime.fromisoformat(data['pushed_at'].replace('Z', '+00:00'))

        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            full_name=data.get('full_name', ''),
            description=data.get('description'),
            private=data.get('private', False),
            owner=owner,
            html_url=data.get('html_url', ''),
            clone_url=data.get('clone_url', ''),
            ssh_url=data.get('ssh_url', ''),
            language=data.get('language'),
            languages=data.get('languages', {}),
            default_branch=data.get('default_branch', 'main'),
            created_at=created_at,
            updated_at=updated_at,
            pushed_at=pushed_at,
            size=data.get('size', 0),
            stars=data.get('stargazers_count', 0),
            forks=data.get('forks_count', 0),
            open_issues=data.get('open_issues_count', 0),
            watchers=data.get('watchers_count', 0),
            archived=data.get('archived', False),
            disabled=data.get('disabled', False),
            license=data.get('license', {}).get('name') if data.get('license') else None
        )


@dataclass
class GitHubCommit:
    """GitHub commit model."""
    sha: str
    message: str
    author: GitHubUser
    committer: GitHubUser
    date: datetime
    html_url: str = ""
    parents: List[str] = None
    stats: Dict[str, int] = None
    files: List[Dict[str, Any]] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'GitHubCommit':
        """Create GitHubCommit from GitHub API response."""
        # Parse commit data
        commit_data = data.get('commit', {})
        author_data = commit_data.get('author', {})
        committer_data = commit_data.get('committer', {})

        # Parse datetime
        date = None
        if author_data.get('date'):
            date = datetime.fromisoformat(author_data['date'].replace('Z', '+00:00'))

        # Create author and committer users
        author = GitHubUser(
            name=author_data.get('name'),
            email=author_data.get('email'),
            login=""  # GitHub API doesn't always provide login for commit authors
        )

        committer = GitHubUser(
            name=committer_data.get('name'),
            email=committer_data.get('email'),
            login=""  # GitHub API doesn't always provide login for committers
        )

        return cls(
            sha=data.get('sha', ''),
            message=commit_data.get('message', ''),
            author=author,
            committer=committer,
            date=date or datetime.now(),
            html_url=data.get('html_url', ''),
            parents=[parent.get('sha', '') for parent in data.get('parents', [])],
            stats=data.get('stats', {}),
            files=data.get('files', [])
        )


@dataclass
class GitHubFileChange:
    """GitHub file change model."""
    filename: str
    status: str  # 'added', 'removed', 'modified', 'renamed', 'copied'
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: Optional[str] = None
    previous_filename: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'GitHubFileChange':
        """Create GitHubFileChange from GitHub API response."""
        return cls(
            filename=data.get('filename', ''),
            status=data.get('status', ''),
            additions=data.get('additions', 0),
            deletions=data.get('deletions', 0),
            changes=data.get('changes', 0),
            patch=data.get('patch'),
            previous_filename=data.get('previous_filename')
        )


@dataclass
class GitHubBranch:
    """GitHub branch model."""
    name: str
    commit: GitHubCommit
    protected: bool = False

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'GitHubBranch':
        """Create GitHubBranch from GitHub API response."""
        commit_data = data.get('commit', {})
        commit = GitHubCommit.from_api_response({'sha': commit_data.get('sha', ''), 'commit': commit_data})

        return cls(
            name=data.get('name', ''),
            protected=data.get('protected', False),
            commit=commit
        )


@dataclass
class GitHubRateLimit:
    """GitHub API rate limit information."""
    limit: int
    remaining: int
    reset: datetime
    used: int = 0
    resource: str = ""

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> 'GitHubRateLimit':
        """Create GitHubRateLimit from HTTP headers."""
        reset = datetime.fromtimestamp(int(headers.get('x-ratelimit-reset', 0)))

        return cls(
            limit=int(headers.get('x-ratelimit-limit', 0)),
            remaining=int(headers.get('x-ratelimit-remaining', 0)),
            reset=reset,
            used=int(headers.get('x-ratelimit-used', 0)),
            resource=headers.get('x-ratelimit-resource', '')
        )


@dataclass
class GitHubError:
    """GitHub API error model."""
    message: str
    documentation_url: Optional[str] = None
    errors: List[Dict[str, Any]] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'GitHubError':
        """Create GitHubError from GitHub API response."""
        return cls(
            message=data.get('message', ''),
            documentation_url=data.get('documentation_url'),
            errors=data.get('errors', [])
        )
