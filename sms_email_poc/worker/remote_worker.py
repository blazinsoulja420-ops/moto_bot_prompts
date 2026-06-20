"""Background worker to capture screen, preprocess, call Gemini/OCR, and generate reports.

Run as a standalone process on the laptop that has access to the TeamViewer window.
"""
import os
import time
from pathlib import Path
import json
import logging

from sms_email_poc.integrations import screen_capture, gemini_client
from sms_email_poc.integrations import gemini_prompts
from sms_email_poc import master_mechanic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('remote_worker')


CAPTURE_INTERVAL = int(os.getenv('CAPTURE_INTERVAL', '10'))  # seconds
OUTPUT_DIR = Path(os.getenv('WORKER_OUTPUT_DIR', 'worker_output'))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def preprocess_image(path: str) -> str:
    """Basic preprocessing: increase contrast and save to a new file."""
    try:
        from PIL import Image, ImageEnhance
        img = Image.open(path)
        enhancer = ImageEnhance.Contrast(img)
        img2 = enhancer.enhance(1.5)
        out = str(Path(path).with_suffix('.proc.png'))
        img2.save(out)
        return out
    except Exception:
        return path


def main_loop():
    logger.info('Starting remote worker loop (interval=%s)', CAPTURE_INTERVAL)
    while True:
        try:
            img = screen_capture.capture_screen()
            if not img:
                logger.warning('No screenshot available; skipping')
                time.sleep(CAPTURE_INTERVAL)
                continue

            proc = preprocess_image(img)
            report_text = None
            gem_res = None

            # Prefer Gemini if configured
            gem_res = gemini_client.analyze_image(proc, prompt=gemini_prompts.build_gemini_prompt())
            if gem_res:
                # try to use JSON response or text
                if isinstance(gem_res, dict) and 'error' not in gem_res:
                    gem_text = gem_res.get('text') or json.dumps(gem_res)
                else:
                    gem_text = str(gem_res)
                report_text = master_mechanic.generate_report(gem_text, ocr_text=None, obd_data=None)
            else:
                # fallback to OCR
                ocr = screen_capture.ocr_image(proc)
                report_text = master_mechanic.generate_report(ocr or '')

            # save outputs
            ts = int(time.time())
            out_report = OUTPUT_DIR / f'report_{ts}.md'
            out_report.write_text(report_text, encoding='utf-8')
            logger.info('Wrote report to %s', out_report)
        except Exception as e:
            logger.exception('Worker error: %s', e)
        time.sleep(CAPTURE_INTERVAL)


if __name__ == '__main__':
    main_loop()
