from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup
import openai
import os
import re
import requests

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_plan', methods=['POST'])
def get_plan():
    disease = request.form.get('disease')
    age = request.form.get('age')
    weight = request.form.get('weight')
    diabetic = request.form.get('diabetic')
    bp = request.form.get('bp')

    # Get height in feet and inches
    height_feet = request.form.get('height_feet')
    height_inches = request.form.get('height_inches')
    height_total_inches = int(height_feet) * 12 + int(height_inches)

    # Create the prompt for generating the plan based on personal details
    prompt = f"""
    Provide a detailed health plan for a {age}-year-old person with {disease}, who weighs {weight} kgs, has a height of {height_total_inches} inches, 
    is diabetic ({diabetic}), and has blood pressure categorized as {bp}. Ensure that the plan is tailored to these details.
    
    1. Include a detailed list of **Symptoms** of {disease}, explaining the symptoms based on the patient's condition.
    2. Suggest the **Foods to Eat** and the **Foods to Avoid** that match the patient's diabetic and blood pressure status.
    3. Provide a **Diet Plan** that suits the patient's age and weight:
        - Breakfast
        - Lunch
        - Evening Snack
        - Dinner
        - Smoothies or Detox Drinks
    4. Recommend yoga exercises suitable for someone with these health conditions, including detailed explanation in points, descriptions and images of the poses.
    5. Suggest **Ayurvedic Herbs and Powders**, with explanations on how they can help manage {disease}, and how to consume them effectively.
    6. Provide **Natural Treatments** with details of any external or herbal therapies that are suitable for this patient.
    7. Finally, add any **Additional Tips** for managing their overall health, based on their diabetic and blood pressure condition.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )

        plan = response['choices'][0]['message']['content'].strip()

        formatted_output = f"""
            <h2><strong>SYMPTOMS</strong></h2>
            {format_explanation(plan)}
            <h2><strong>NUTRITION</strong></h2>
            {format_diet(plan)}
            <h2><strong>YOGA</strong></h2>
            {format_yoga(plan)}
            <h2><strong>HERBS</strong></h2>
            {format_herbs(plan)}
            <h2><strong>NATURAL TREATMENTS</strong></h2>
            {format_treatments(plan)}
            <h2><strong>ADDITIONAL TIPS</strong></h2>
            {format_tips(plan)}
        """
        return jsonify({"output": formatted_output})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)})

def format_explanation(plan):
    explanation = re.search(r"(Symptoms)(.*?)(Foods to Eat|Foods to Avoid|Diet Plan|$)", plan, re.DOTALL | re.IGNORECASE)

    if explanation:
        cleaned_explanation = clean_markdown(explanation.group(2))
        cleaned_explanation = re.sub(r"of\s+[A-Za-z\s]+", "", cleaned_explanation)  
        cleaned_explanation = cleaned_explanation.strip() 
        return cleaned_explanation
    return "No explanation available"

def format_diet(plan):
    foods_to_eat_match = re.search(r"(Foods to Eat)(.*?)(Foods to Avoid|Diet Plan|Yoga|$)", plan, re.DOTALL | re.IGNORECASE)
    foods_to_eat_content = foods_to_eat_match.group(2).strip() if foods_to_eat_match else "No foods to eat available."
    
    foods_to_eat_content = re.sub(r'and\s+Avoid', '', foods_to_eat_content, flags=re.IGNORECASE).strip()  
    foods_to_eat_content = re.sub(r'Foods to Eat', '', foods_to_eat_content, flags=re.IGNORECASE).strip()
    
    foods_to_avoid_match = re.search(r"(Foods to Avoid)(.*?)(Diet Plan|Yoga|$)", plan, re.DOTALL | re.IGNORECASE)
    foods_to_avoid_content = foods_to_avoid_match.group(2).strip() if foods_to_avoid_match else "No foods to avoid available."


    diet_plan_match = re.search(r"(Diet Plan)(.*?)(Yoga|$)", plan, re.DOTALL | re.IGNORECASE)
    diet_plan_content = diet_plan_match.group(2).strip() if diet_plan_match else "No diet plan available."

    formatted_diet = ""

    if foods_to_eat_content:
        formatted_diet += f"<h3>Foods to Eat</h3>{clean_markdown(foods_to_eat_content)}"

    if foods_to_avoid_content:
        formatted_diet += f"<h3>Foods to Avoid</h3>{clean_markdown(foods_to_avoid_content)}"

    if diet_plan_content:
        formatted_diet += f"<h3>Diet Plan</h3>{clean_markdown(diet_plan_content)}"

    return formatted_diet


def fetch_image_url(pose_name):
    API_KEY = os.getenv('API_KEY')
    CSE_ID = os.getenv('CSE_ID')

    # Clean the pose_name to remove HTML tags and unnecessary characters
    clean_pose_name = BeautifulSoup(pose_name, "html.parser").text.strip()

    search_url = f"https://www.googleapis.com/customsearch/v1?q={clean_pose_name}+Pose&cx={CSE_ID}&key={API_KEY}&searchType=image&num=1&siteSearch=yogajournal.com"
    
    try:
        response = requests.get(search_url)
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            image_url = data['items'][0]['link']
            return image_url
        else:
            print(f"No image found for {pose_name}. API response: {data}")
            return "Image not found."
    except Exception as e:
        print(f"Error fetching image for {pose_name}: {str(e)}")
        return "Image not found."


def format_yoga(plan):
    yoga_exercises = re.search(r"(Yoga Exercises)(.*?)(Herbs|$)", plan, re.DOTALL | re.IGNORECASE)
    if yoga_exercises:
        yoga_content = clean_markdown(yoga_exercises.group(2))
        
        def replace_with_image(match):
            pose_name = match.group(1)
            image_url = fetch_image_url(pose_name)
            return f'<strong>{pose_name}:</strong><br><img src="{image_url}" alt="{pose_name} Pose" width="200"><br>'
        
        yoga_content_with_images = re.sub(r'<strong>(.*?)<\/strong>', replace_with_image, yoga_content)
        return yoga_content_with_images
    return "No yoga exercises available"

def format_herbs(plan):
    herbs = re.search(r"(Herbs)(.*?)(Natural Treatments|$)", plan, re.DOTALL | re.IGNORECASE)
    if herbs:
        return clean_markdown(herbs.group(2))
    return "No herbs available"

def format_treatments(plan):
    treatments = re.search(r"(Natural Treatments)(.*?)(Additional Tips|$)", plan, re.DOTALL | re.IGNORECASE)
    if treatments:
        return clean_markdown(treatments.group(2))
    return "No natural treatments available"

def format_tips(plan):
    additional_tips = re.search(r"(Additional Tips)(.*)", plan, re.DOTALL | re.IGNORECASE)
    if additional_tips:
        return clean_markdown(additional_tips.group(2))
    return "No additional tips available"

def clean_markdown(text):
    text = re.sub(r'\*\*', '', text)  
    text = re.sub(r'Detailed', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(<h\d>.*?</h\d>)\s*<br>', r'\1', text)
    
    text = re.sub(r'(\b\w+):(?=\s)', r'<strong>\1:</strong>', text)
    text = re.sub(r'(\d{1,2}):(\d{2})\s?([AP]M)', r'\1:\2 \3', text)  
    text = re.sub(r'(\d{1,2}:\d{2}\s?[AP]M)', r'\1', text)
    text = re.sub(r'(?<!\d)(.*?):(?!\d{2}\s?[AP]M)', r'<strong>\1</strong>:', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text) 
    text = re.sub(r'https?:\/\/\S+', '', text) 
    text = re.sub(r'(.*?):', r'<br><strong>\1:</strong>', text)

    text = re.sub(r'and\s(?!(Symptoms|Nutrition|Yoga|Herbs|Natural Treatments|Additional Tips))\s.*?(?=\n|<br>)', '', text)
    text = re.sub(r'for\s.*?(?=\n<br>)', '', text)
    text = re.sub(r'and Powders\s.*?(?=\n|<br>)', '', text)
    text = re.sub(r'\bAyurvedic\b', '', text)
    text = re.sub(r'\bExercises\b', '', text)
    
    text = re.sub(r'\b(for\s+\w+)\b', '', text)  
    text = re.sub(r'(<h3>.*?</h3>):', r'\1', text) 
    text = re.sub(r'\n\s*\n+', '\n', text)  
    text = re.sub(r'!\[.*?\]', '', text)
    text = re.sub(r'###', '', text)  
    text = re.sub(r'#', '', text)  
    
    text = re.sub(r'(\s*-\s*)?<strong>(.*?)<\/strong>', r'<strong>\2</strong>', text)
    text = re.sub(r'-\s*<strong>', '-', text)
    text = re.sub(r'^\s*-\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?<!\d)(.*?):(?!\d{2}\s?[AP]M)', r'<strong>\1</strong>', text)
    text = re.sub(r'-\s*<strong>', '<strong>', text) 
    text = re.sub(r'-\s*(<h\d>|<strong>)', r'\1', text)
    text = re.sub(r'and\s+symptoms\s+of\s+[A-Za-z\s]+', '', text, flags=re.IGNORECASE)

    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)  
    text = re.sub(r'\d+\.', '', text)
 
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\n', '<br>', text)
    text = text.replace("\n", "<br>")
    text = re.sub(r'(<br>\s*)+', r'<br>', text)

    text = text.replace("<br><br>", "<br>")
    text = re.sub(r'(<br>)+', r'<br><br>', text) 
    text = re.sub(r'(<br>)+$', '', text)
    text = re.sub(r'<br>$', '', text) 
    text = re.sub(r'<h2>', r'<br><h2>', text)
    text = text.strip().replace("<br><br>", "<br>")
    
    return text

if __name__ == '__main__':
    app.run(debug=True)
