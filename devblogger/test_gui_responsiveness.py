#!/usr/bin/env python3
"""
Simple GUI responsiveness test to isolate the issue
"""

import customtkinter as ctk
import threading
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("GUI Responsiveness Test")
        self.geometry("400x300")
        
        # Create test button
        self.test_button = ctk.CTkButton(
            self,
            text="Test Button",
            command=self.on_button_click
        )
        self.test_button.pack(pady=20)
        
        # Create status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready - Click the button to test responsiveness"
        )
        self.status_label.pack(pady=10)
        
        # Click counter
        self.click_count = 0
        
    def on_button_click(self):
        self.click_count += 1
        logger.info(f"🔴 BUTTON CLICKED #{self.click_count} - GUI is responsive!")
        self.status_label.configure(text=f"Button clicked {self.click_count} times - GUI is working!")
        
        # Test background thread
        def background_task():
            logger.info("Background task started")
            time.sleep(2)
            logger.info("Background task completed")
            self.after(0, lambda: self.status_label.configure(text=f"Background task completed (clicks: {self.click_count})"))
        
        threading.Thread(target=background_task, daemon=True).start()

if __name__ == "__main__":
    logger.info("Starting GUI responsiveness test...")
    
    app = TestWindow()
    
    logger.info("GUI created, starting main loop...")
    app.mainloop()
    
    logger.info("GUI closed")
