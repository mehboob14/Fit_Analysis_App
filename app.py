import os
import asyncio
import json
import uuid
import shutil
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for
from scraper.upd_1 import run_scrape_and_save
from scraper.upd_structure import run_structure
from scraper.Scripts.upd_fabric_analysis import run_fabric_analysis_from_json
from scraper.Scripts.upd_flare_analysis import run_flare_analysis_from_json
from scraper.Scripts.upd_waist_analysis import run_waist_analysis_from_json
# from scraper.Scripts.upd_hip_analysis import run_hip_analysis_from_json
# from scraper.Scripts.upd_skirt_analysis import run_skirt_analysis_from_json
from scraper.Scripts.upd_bodice import run_Bodice_analysis_from_json
from scraper.Scripts.upd_back import run_Back_analysis_from_json
from scraper.Scripts.upd_oneShoulder import run_One_Shoulder_analysis_from_json
from scraper.Scripts.upd_seleeves import run_Seleevs_analysis_from_json
from scraper.Scripts.upd_Neckline import run_neckline_analysis_from_json
from scraper.Scripts.upd_hemline import run_Hemline_analysis_from_json
from scraper.Scripts.Script import run_fit_analysis

from concurrent.futures import ProcessPoolExecutor

app = Flask(__name__)
app.static_folder = 'static'

executor = ProcessPoolExecutor(max_workers=5)

def run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, func, *args)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('dress_url')
        front_image = request.files.get('front_image')
        side_image = request.files.get('side_image')
        action = request.form.get('action')

        if not front_image or not side_image:
            return render_template('index.html', error="Please upload both front and side images")

        if not url:
            return render_template('index.html', error="Please enter a URL")

        upload_folder = os.path.join(app.root_path, 'static', 'images', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        front_filename = secure_filename(front_image.filename)
        side_filename = secure_filename(side_image.filename)

        _, front_ext = os.path.splitext(front_filename)
        _, side_ext = os.path.splitext(side_filename)

        front_unique = f"front_{uuid.uuid4().hex}{front_ext}"
        side_unique = f"side_{uuid.uuid4().hex}{side_ext}"

        front_image_path = os.path.join(upload_folder, front_unique)
        side_image_path = os.path.join(upload_folder, side_unique)

        front_image.save(front_image_path)
        side_image.save(side_image_path)

        print(f"Front image saved to: {front_image_path}")
        print(f"Side image saved to: {side_image_path}")

        # Always define path outside try
        analysis_json_path = None

        try:
            if action == "analyze":
                print("[DEBUG] Starting scrape...")
                run_scrape_and_save(url)
                print("[DEBUG] Scrape done. Starting structure...")
                run_structure()
                print("[DEBUG] Structure done.")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                tasks = [
                    run_in_executor(run_fabric_analysis_from_json),
                    run_in_executor(run_flare_analysis_from_json),
                    run_in_executor(run_waist_analysis_from_json),
                    # run_in_executor(run_hip_analysis_from_json),
                    # run_in_executor(run_skirt_analysis_from_json),
                    run_in_executor(run_Bodice_analysis_from_json),
                    run_in_executor(run_Back_analysis_from_json),
                    run_in_executor(run_One_Shoulder_analysis_from_json),
                    run_in_executor(run_Seleevs_analysis_from_json),
                    run_in_executor(run_neckline_analysis_from_json),
                    run_in_executor(run_Hemline_analysis_from_json)
                ]

                results = loop.run_until_complete(asyncio.gather(*tasks))
                # print(f"[DEBUG] Analysis tasks completed. Results: {results}")

                keys = [
                    'fabric_analysis', 'flare_analysis',
                    'waist_analysis',
                    # 'hip_analysis',
                    # 'skirt_analysis',
                    'bodice_analysis', 'back_analysis',
                    'one_shoulder_analysis', 'sleeves_analysis',
                    'neckline_analysis', 'hemline_analysis'
                ]

                if len(keys) != len(tasks):
                    raise Exception("Mismatch: keys and tasks length must match!")

                analysis_results = {k: v for k, v in zip(keys, results) if v}
                print(f"[DEBUG] Compiled analysis_results: {analysis_results}")

                if not analysis_results:
                    raise Exception("No analysis results produced!")

                os.makedirs('data', exist_ok=True)
                analysis_json_path = os.path.join('data', 'analysis_results.json')
                with open(analysis_json_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis_results, f, ensure_ascii=False, indent=2)

                print(f"[DEBUG] Analysis results written to {analysis_json_path}")

                conclusion = run_fit_analysis(front_image_path, side_image_path, analysis_json_path)
                print("Fit analysis conclusion:", conclusion)

                script_data_path = os.path.join('scraper', 'Scripts', 'data')
                if os.path.exists(script_data_path):
                    shutil.rmtree(script_data_path)

                return redirect(url_for('output'))

            else:
                return render_template('index.html', error="Unknown action.")

        except Exception as e:
            print(f"[ERROR] Exception: {str(e)} | analysis_json_path: {analysis_json_path}")
            return render_template('index.html', error=f"Error: {str(e)}")

    return render_template('index.html')

@app.route('/output')
def output():
    try:
        with open('data/analysis_results.json', 'r', encoding='utf-8') as f:
            analysis = json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not load output: {str(e)}")
        analysis = {}
    return render_template('output.html', analysis=analysis)

@app.route('/result')
def result():
    try:
        with open('data/result.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        image_dir = 'static/images/downloaded'
        os.makedirs(image_dir, exist_ok=True)

        images = os.listdir(image_dir)
        images = [url_for('static', filename=f'images/downloaded/{img}') for img in images]
    except Exception as e:
        return f"Error loading result: {str(e)}"

    return render_template('result.html', data=data, images=images)

if __name__ == '__main__':
    app.run(threaded=True, debug=True)
