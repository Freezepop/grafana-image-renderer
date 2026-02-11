#!/usr/bin/python3.8

import io
import time
import numpy
import tempfile
import requests
import urllib3
from PIL import Image
from os import getenv
from flask import Flask, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
urllib3.disable_warnings()

app = Flask(__name__)

CHROME_BIN = getenv("CHROME_BIN", "/usr/lib64/chromium-browser/chromium-browser")
CHROMEDRIVER_PATH = getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

GRAFANA_URL = getenv("GRAFANA_URL", "")
GRAFANA_USER = getenv("GRAFANA_USER", "")
GRAFANA_PASS = getenv("GRAFANA_PASS", "")


def get_grafana_session_cookie() -> str:
    login_url = f"{GRAFANA_URL}/login"
    resp = requests.post(
        login_url,
        json={"user": GRAFANA_USER, "password": GRAFANA_PASS},
        allow_redirects=False,
        verify=False
    )
    if resp.status_code not in (200, 302):
        raise RuntimeError(f"Failed to login to Grafana: {resp.status_code} {resp.text}")

    cookie = resp.cookies.get("grafana_session")
    if not cookie:
        raise RuntimeError("No grafana_session cookie returned from Grafana")
    print("[INFO] Logged in to Grafana successfully")
    return cookie


def render_grafana_image(url: str, width=1000, height=500, scale=1.0, timeout=30):
    options = Options()
    options.binary_location = CHROME_BIN
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors=true")
    options.add_argument(f"--window-size={int(width * scale)},{int(height * scale)}")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        cookie_value = get_grafana_session_cookie()

        driver.get(GRAFANA_URL)
        driver.add_cookie({
            "name": "grafana_session",
            "value": cookie_value,
            "path": "/"
        })

        print(f"[INFO] Opening URL: {url}")
        driver.get(url)

        wait_for_visual_stability(driver, selector="body", timeout=timeout, check_interval=1)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        driver.save_screenshot(tmp.name)
        print(f"[INFO] Screenshot saved to {tmp.name}")
        return tmp.name

    finally:
        driver.quit()


def get_avg_color(png_bytes):
    img = Image.open(io.BytesIO(png_bytes))
    arr = numpy.array(img)
    if arr.ndim == 3:
        rgb = arr[:, :, :3]
        return rgb.mean(axis=(0, 1))
    return numpy.array([0, 0, 0])


def wait_for_visual_stability(driver, selector, timeout, check_interval):

    stat_time = time.time()
    prev_color = None

    counter = 0

    while time.time() - stat_time < timeout:
        el = driver.find_element(By.CSS_SELECTOR, selector)
        png = el.screenshot_as_png
        avg_color = get_avg_color(png)

        if prev_color is not None:
            diff = numpy.abs(avg_color - prev_color).mean()
            if diff == 0:
                if counter < 3:
                    counter += 1
                else:
                    print(f"[INFO] Visual stability reached (delta={diff:2f})")
                    return True
            else:
                print(f"[DEBUG] delta={diff:2f}, waiting...")

        prev_color = avg_color
        time.sleep(check_interval)

    print("[WARN] Timeout waiting for visual stability")
    return False


@app.route("/render")
def render():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    width = int(request.args.get("width", 1000))
    height = int(request.args.get("height", 500))
    scale = float(request.args.get("deviceScaleFactor", 1.0))
    timeout = int(request.args.get("timeout", 30))

    file_path = render_grafana_image(url, width, height, scale, timeout)
    return send_file(file_path, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True)
