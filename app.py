from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import time
import os
import re
import requests

app = Flask(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def fetch_image_url(pose_name):
    API_KEY = os.getenv('API_KEY')
    CSE_ID = os.getenv('CSE_ID')

    clean_pose_name = pose_name.strip().replace(" ", "+")
    search_url = f"https://www.googleapis.com/customsearch/v1?q={clean_pose_name}+Yoga+Pose&cx={CSE_ID}&key={API_KEY}&searchType=image&num=1"

    max_retries = 3
    timeout = 10
    wait_time = 5  

    for attempt in range(max_retries):
        try:
            response = requests.get(search_url, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if 'items' in data and data['items']:
                for item in data['items']:
                    image_url = item['link']
                    if 'yoga' in image_url.lower():
                        return image_url
                return data['items'][0]['link']

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                wait_time *= 2 

    print(f"Failed to fetch image for {pose_name} after {max_retries} attempts.")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_plan', methods=['POST'])
def get_plan():
    diseases = request.form.getlist('disease') 
    age = request.form.get('age')
    weight = request.form.get('weight')
    diabetic = request.form.get('diabetic')
    bp = request.form.get('bp')

    height_feet = request.form.get('height_feet')
    height_inches = request.form.get('height_inches')
    height_total_inches = int(height_feet) * 12 + int(height_inches)

    disease_str = ', '.join(diseases)

    prompt = f"""
    HEALTH PLANNER as heading in the center of the page
    
    Generate a detailed health plan for a {age}-year-old person with the following diseases: {', '.join(diseases)}, 
    who weighs {weight} kgs, has a height of {height_total_inches} inches, is diabetic ({diabetic}), and has blood pressure categorized as {bp}. Ensure that the plan is tailored to these details.
    
    <br><strong>DETAILS</strong>
    <br>Disease/Condition: {disease_str} 
    <br>Age: {age} 
    <br>Weight: {weight} kgs 
    <br>Height: {height_total_inches} inches 
    <br>Diabetic: {diabetic} 
    <br>Blood Pressure: {bp}
    <br>
    """

    for disease in diseases:
        prompt += f"""
        <br><br><strong>SYMPTOMS</strong><br>
        <br> Provide a detailed list of symptoms for {disease}, explaining how they may manifest based on the patient's condition.

        <br><br><br><strong>FOODS TO EAT</strong>
        <br>Suggest and list foods suitable for the patient's age, diabetes, and blood pressure status for managing {disease}. Each food should be listed as a point starting in a new line.
        
        <br><br><br><strong>FOODS TO AVOID</strong>
        <br>Suggest and list foods that should be avoided, considering the patient's age, diabetes, and blood pressure status while managing {disease}. Each food should be listed as a point starting in a new line.
        
        <br><br><br><strong>HERBS</strong>
        <br>Suggest herbs, spices, plants, roots, and powders for managing and/or curing {disease} based on their age, diabetes, and blood pressure. Include how they should be consumed for maximum benefit.
  
        <br><br><strong>YOGA</strong><br>
        <br>Suggest all yoga poses to help manage or alleviate {disease} and speed up the healing process including images of the asana with description and benefits of the pose.
        """
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            plan = response.text.strip()

            pose_names = re.findall(r'[a-zA-Z\s]+ Pose', plan)
            plan_with_images = []

            for pose_name in pose_names:
                image_url = fetch_image_url(pose_name)  # Fetch image URL here
                if image_url:
                    plan_with_images.append(f"<li><strong>{pose_name}</strong><br>\n<img src='{image_url}' alt='{pose_name} Pose' style='width:250px;'><br></li>")
                else:
                    plan_with_images.append(f"<li><strong>{pose_name}</strong><br>\nNo image found.<br></li>")
            
            prompt += "<ul>" + "".join(plan_with_images) + "</ul>"

        except Exception as e:
            print(f"Error: {str(e)}")
            prompt += "<li>Error fetching yoga poses.<br></li>"


        prompt += f"""
        <br><br><br><strong>DIET PLAN</strong>
        <br>Provide a diet plan for the patient as per the {disease} to help manage or alleviate {disease} with all kinds of traditional and healthy foods.
        Provide the recipe for each plan starting in a new line.

        <br><br><br><strong>SMOOTHIES OR DETOX DRINKS</strong>
        <br>List suitable smoothies, fruit juices, or detox drinks as points starting in a new line for managing their condition.
        
        <br><br><br><strong>NATURAL TREATMENTS</strong>
        <br>Suggest natural treatments, including home remedies and herbal therapies, to help manage their conditions and improve immunity. List treatments in points.
        
        <br><br><br><strong>ADDITIONAL METHODS</strong>
        <br>List any additional methods or lifestyle changes for managing overall health based on their diabetes and blood pressure.<br>
        """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        plan = response.text.strip()
        formatted_plan = format_plan(plan)
        return jsonify({"output": formatted_plan})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)})


def format_plan(text):

    text = re.sub(r'#+\s*HEALTH PLANNER', r'<div style="text-align:center;"><strong>HEALTH PLANNER</strong></div>', text)

    heading_pattern = re.compile(r'\*\*([A-Z\s]+):\*\*')
    text = heading_pattern.sub(r'<h3><strong>\1</strong></h3>', text)

    bold_pattern = re.compile(r'\*\*([^\*]+)\*\*')
    text = bold_pattern.sub(r'<br><strong>\1</strong>', text) 

    text = re.sub(r'\[Image of [^\]]+\]', '', text)
    text = re.sub(r'\[.*?\]\(https?://[^\)]+\)', '', text)
    
    text = re.sub(r'\*+', '', text)

    return text


if __name__ == '__main__':
    app.run(debug=True)
