import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def verify_tools():
    from backend.tools.desktop_tools import take_system_screenshot, list_desktop_windows
    
    print("--- Testing list_desktop_windows ---")
    windows_result = await list_desktop_windows()
    if "error" in windows_result:
        print(f"Error listing windows: {windows_result['error']}")
    else:
        print(f"Success! Found {len(windows_result['windows'])} windows.")
        # Print first 5 for verification
        for win in windows_result['windows'][:5]:
            print(f"  - {win['title']} (PID: {win['pid']})")
            
    print("\n--- Testing take_system_screenshot ---")
    screenshot_result = await take_system_screenshot()
    if "error" in screenshot_result:
        print(f"Error taking screenshot: {screenshot_result['error']}")
    else:
        print(f"Success! Screenshot saved to: {screenshot_result['file_path']}")
        print(f"Resolution: {screenshot_result['resolution']}")

if __name__ == "__main__":
    asyncio.run(verify_tools())
