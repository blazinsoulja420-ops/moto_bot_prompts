import asyncio
import re
import sys
from pathlib import Path

# Ensure the workspace root (two levels up) is on sys.path so imports work when
# running the script directly from the venv python executable.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sms_email_poc.handlers import process_message


async def run():
    sender = "+15550001111"
    # Step 1: request remote diagnose with pasted X431 snippet
    req = "remote diagnose x431: P0300, RPM: 800, STFT: -5"
    print('--- Sending request ---')
    resp = await process_message('telegram', sender, req)
    print(resp)

    # extract token from response
    m = re.search(r'Token:\s*([0-9a-fA-F]+)', resp)
    if not m:
        print('No token found; aborting')
        return
    token = m.group(1)
    print('--- Confirming token', token, '---')
    conf = await process_message('telegram', sender, f'confirm {token}')
    print(conf[:2000])


if __name__ == '__main__':
    asyncio.run(run())
