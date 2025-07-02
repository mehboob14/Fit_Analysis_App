import os
import asyncio
import json
from flask import Flask, render_template, request, redirect, url_for
from scraper.upd_1 import run_scrape_and_save
from scraper.upd_structure import run_structure
from scraper.Scripts.upd_fabric_analysis import run_fabric_analysis_from_json
from scraper.Scripts.upd_flare_analysis import run_flare_analysis_from_json
from scraper.Scripts.upd_waist_analysis import run_waist_analysis_from_json
from scraper.Scripts.upd_hip_analysis import run_hip_analysis_from_json
from scraper.Scripts.upd_skirt_analysis import run_skirt_analysis_from_json
from scraper.Scripts.upd_bodice import run_Bodice_analysis_from_json
from scraper.Scripts.upd_back import run_Back_analysis_from_json
from scraper.Scripts.upd_oneShoulder import run_One_Shoulder_analysis_from_json
from scraper.Scripts.upd_seleeves import run_Seleevs_analysis_from_json
from scraper.Scripts.upd_Neckline import run_neckline_analysis_from_json
from scraper.Scripts.upd_hemline import run_Hemline_analysis_from_json

import shutil
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.static_folder = 'static'

executor = ThreadPoolExecutor(max_workers=5)  

def run_async(func, *args):
    try:
        return asyncio.get_event_loop().run_until_complete(func(*args))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(func(*args))

def run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, func, *args)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('dress_url')
        action = request.form.get('action')
        if not url:
            return render_template('index.html', error="Please enter a URL")

        try:
            # if action == "scrape":
            #     data = run_async(scrape_dress, url)
            #     os.makedirs('data', exist_ok=True)
            #     with open('data/result.json', 'w', encoding='utf-8') as f:
            #         json.dump(data, f, ensure_ascii=False, indent=2)
            #     return redirect(url_for('result'))

            if action == "analyze":
                run_scrape_and_save(url)
                run_structure()

                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tasks = [
                    run_in_executor(run_fabric_analysis_from_json),
                    run_in_executor(run_flare_analysis_from_json),
                    run_in_executor(run_waist_analysis_from_json),
                    run_in_executor(run_hip_analysis_from_json),
                    run_in_executor(run_skirt_analysis_from_json),
                    run_in_executor(run_Bodice_analysis_from_json),
                    run_in_executor(run_Back_analysis_from_json),
                    run_in_executor(run_One_Shoulder_analysis_from_json),
                    run_in_executor(run_Seleevs_analysis_from_json),
                    run_in_executor(run_neckline_analysis_from_json),
                    run_in_executor(run_Hemline_analysis_from_json)

                ]
                results = loop.run_until_complete(asyncio.gather(*tasks))
                analysis_results = {}
                keys = [
                    'fabric_analysis', 'flare_analysis',
                    'waist_analysis', 'hip_analysis', 'skirt_analysis',
                    'bodice_analysis', 'back_analysis',
                    'one_shoulder_analysis', 'sleeves_analysis',
                    'neckline_analysis', 'hemline_analysis'
                ]
                for k, v in zip(keys, results):
                    if v:
                        analysis_results[k] = v

                os.makedirs('data', exist_ok=True)
                with open('data/analysis_results.json', 'w', encoding='utf-8') as f:
                    json.dump(analysis_results, f, ensure_ascii=False, indent=2)

                script_data_path = os.path.join('scraper', 'Scripts', 'data')
                if os.path.exists(script_data_path):
                    shutil.rmtree(script_data_path)
                return redirect(url_for('output'))

            else:
                return render_template('index.html', error="Unknown action.")

        except Exception as e:
            return render_template('index.html', error=f"Error: {str(e)}")

    return render_template('index.html')

@app.route('/output')
def output():
    try:
        with open('data/analysis_results.json', 'r', encoding='utf-8') as f:
            analysis = json.load(f)
    except Exception as e:
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