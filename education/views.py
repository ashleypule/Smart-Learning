from django.shortcuts import render, redirect
from .models import Grade, Subject, Question
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import random
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from groq import Groq
import os
from dotenv import load_dotenv 
from django.conf import settings
import time
from django.http import HttpResponseBadRequest
from googleapiclient.discovery import build
from .forms import DocumentUploadForm, TopicForm, QuizForm
from PIL import Image
import pytesseract
from docx import Document
import pypdf
from gtts import gTTS
from playsound import playsound
import pyttsx3
import threading
import pythoncom
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
import openai
from django.shortcuts import render
import json
import requests
from .forms import SolutionForm
from .models import Solution
import pytesseract
import tempfile
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import base64
import io
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import fitz 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key =  OPENAI_API_KEY
client = Groq(api_key=settings.GROQ_API_KEY)
youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = settings.SEARCH_ENGINE_ID

def home(request):
    return render(request, 'home.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('select_grade')
    return render(request, 'login.html')


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')
        
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('select_grade')

    return render(request, 'signup.html')

@login_required
def select_school_level(request):
    if request.method == 'POST':
        selected_level = request.POST.get('level')
        request.session['selected_level'] = selected_level
        return redirect('select_grade')
    
    return render(request, 'select_school_level.html')


@login_required
def select_grade(request):
    if 'selected_level' not in request.session:
        return redirect('select_school_level')

    if request.method == 'POST':
        grade_id = request.POST.get('grade')
        request.session['grade_id'] = grade_id
        return redirect('select_subject')
    
    selected_level = request.session['selected_level']
    grades = Grade.objects.filter(level=selected_level)
    
    return render(request, 'select_grade.html', {'grades': grades})


@login_required
def select_subject(request):
    grade_id = request.session.get('grade_id')
    if request.method == 'POST':
        subject_id = request.POST['subject']
        request.session['subject_id'] = subject_id
        return redirect('generate_content')

    subjects = Subject.objects.filter(grade_id=grade_id)
    return render(request, 'select_subject.html', {'subjects': subjects})


def fetch_youtube_video(query):
    try:
        request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            order='relevance',
            maxResults=1
        )
        response = request.execute()
        
        items = response.get('items', [])
        if items:
            video_id = items[0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print(f"Error fetching YouTube video: {e}")
    
    return ""


# Function to read the document
def read_document(file_path, file_name):
    if file_name.lower().endswith(('.pdf')):
        return read_pdf(file_path)
    elif file_name.lower().endswith(('.docx', '.doc')):
        return read_word(file_path)
    elif file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        return read_image(file_path)
    elif file_name.lower().endswith(('.txt')):
        return read_text(file_path)
    else:
        return "Unsupported file type."


def read_pdf(file_path):
    try:
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = pypdf.PdfReader(pdf_file)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text() or ''
            return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return "Error reading PDF."


def read_word(file_path):
    try:
        doc = Document(file_path)
        text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
        return text
    except Exception as e:
        print(f"Error reading Word document: {e}")
        return "Error reading Word document."


def read_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error reading image: {e}")
        return "Error reading image."


def read_text(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading text file: {e}")
        return "Error reading text file."


def speak_text(text, filename):
    """Function to read text aloud and save it as an audio file using pyttsx3."""
    pythoncom.CoInitialize()  # Initialize COM
    engine = pyttsx3.init()
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'audio', filename)
    
    print(f"Saving audio to: {audio_file_path}")  # Debug print

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)

    try:
        engine.save_to_file(text, audio_file_path)
        engine.runAndWait()
        print("Audio file created successfully.")  # Debug print
    except Exception as e:
        print(f"Error saving audio file: {e}")
        return None

    return audio_file_path



@login_required
def ask_question(request):
    answer = ""
    video_url = ""
    document_content = ""
    question = ""
    audio_file_url = ""

    if request.method == 'POST':
        uploaded_file = request.FILES.get('document')
        question = request.POST.get("question")
        audio_filename = f"audio_{int(time.time())}.mp3"

        if uploaded_file:
            documents_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
            os.makedirs(documents_dir, exist_ok=True)
            file_path = os.path.join(documents_dir, uploaded_file.name)

            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            document_content = read_document(file_path, uploaded_file.name)
            print("Extracted Document Content:", document_content)

            if not document_content or "Error" in document_content:
                document_content = "No content extracted from the document."
            else:
                question = document_content
                video_query = f"{question}"
                video_url = fetch_youtube_video(video_query)
                video_url = video_url.replace('watch?v=', 'embed/')

            context = (
                f"You are a helpful assistant. "
                f"Provide a detailed, step-by-step guide on how to solve the following question or topic: {question}. "
                f"Include any relevant information."
            )

            answer = generate_answer(context)
            os.remove(file_path)

        elif question:
            context = (
                f"You are a helpful assistant. "
                f"Provide a detailed, step-by-step guide on how to solve the following question or topic: {question}. "
                f"Include any relevant information."
            )

            answer = generate_answer(context)

            video_query = f"{question}"
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')

        else:
            answer = "No document or question was submitted."

        # Generate audio file for the answer
        if answer:
            audio_file_path = speak_text(answer, audio_filename)
            if audio_file_path:
                audio_file_url = f"{settings.MEDIA_URL}audio/{audio_filename}"

        # Generate quiz questions based on the question content
        if question:  # Ensure that question is used to generate new questions
            result = generate_questions(question)  # Use question as topic

            if result:  # Check if result is not empty
                questions = result  # Assuming result is a list of question dictionaries
                request.session['questions'] = questions
                request.session['attempted_questions'] = [False] * len(questions)
                request.session['user_answers'] = [None] * len(questions)
            else:
                print("No questions generated for the provided topic.")


    return render(request, 'ask_question.html', {
        'document_content': document_content,
        'question': question,
        'answer': answer,
        'video_url': video_url,
        'audio_file_url': audio_file_url,
        'MEDIA_URL': settings.MEDIA_URL,
    })



@login_required
def generate_content(request):
    # Fetch values from the session
    selected_level = request.session.get('selected_level', 'Unknown Level')
    grade_name = request.session.get('grade_name', 'Unknown Grade')
    subject_name = request.session.get('subject_name', 'Unknown Subject')

    grade_id = request.session.get('grade_id', 'Unknown Grade')
    subject_id = request.session.get('subject_id', 'Unknown Subject')

    answer = ""
    video_url = ""
    audio_file_url = ""
    image_urls = []

    if request.method == "POST":
        selected_topic = request.POST.get("topic")

        # Generate a unique filename for the audio
        audio_filename = f"audio_{int(time.time())}.mp3"

        if selected_topic:
            context = (
                f"You are an assistant for a school system. "
                f"The current school level is '{selected_level}', "
                f"the grade is '{grade_id}', and the subject is '{subject_id}'. "
                f"Elaborate on the topic: {selected_topic}. "
                f"You can include any relevant information."
            )
            
            start = time.process_time()
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides comprehensive solutions."},
                    {"role": "user", "content": context}
                ],
                model="llama3-8b-8192",
                temperature=0.5,
                max_tokens=1024,
                top_p=1,
                stop=None,
                stream=False,
            )
            answer = chat_completion.choices[0].message.content
            end = time.process_time()
            print(f"Processing time: {end - start} seconds")

            # Generate audio for the answer
            audio_file_path = speak_text(answer, audio_filename)  # Pass unique filename
            if audio_file_path:
                audio_file_url = f"{settings.MEDIA_URL}audio/{audio_filename}"  # Use the unique filename

            # Fetch the video URL based on the topic
            video_query = selected_topic
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')

            # Fetch image URLs based on the topic
            image_urls = google_image_search(GOOGLE_API_KEY, SEARCH_ENGINE_ID, selected_topic)

        else:
            answer = "No topic was submitted."
    
    return render(request, 'generate_content.html', {
        'answer': answer,
        'video_url': video_url,
        'audio_file_url': audio_file_url, 
        'image_urls': image_urls
    })


def google_image_search(api_key, cse_id, query, num_results=2):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cse_id,
        'q': query,
        'searchType': 'image',
        'num': num_results
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        results = response.json()
        image_urls = [item['link'] for item in results.get('items', [])]
        return image_urls
    else:
        print("Error:", response.status_code, response.text)
        return []


    def is_valid_answer(answer, selected_level, grade_name, subject_name):
        if selected_level in answer and grade_name in answer and subject_name in answer:
            return True
        return False


def is_valid_answer(answer, selected_level, grade_name, subject_name):
    if selected_level in answer and grade_name in answer and subject_name in answer:
        return True
    return False


def is_valid_answer(answer, selected_level, grade_id, subject_id):
    """
    Validate if the answer is relevant to the specified level, grade, and subject.
    This is a placeholder function and should be implemented based on specific criteria.
    """
    if not answer:
        return False

    if (selected_level.lower() in answer.lower() or 
        grade_id.lower() in answer.lower() or 
        subject_id.lower() in answer.lower()):
        return True

    return False


def generate_answer(context):
    start = time.process_time()
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides comprehensive solutions."},
                {"role": "user", "content": context}
            ],
            model="llama3-8b-8192",
            temperature=0.5,
            max_tokens=1024,
            top_p=1,
            stop=None,
            stream=False,
        )
        answer = chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error generating answer: {e}")
        answer = "Error generating answer."
    end = time.process_time()
    print(f"Processing time for generation: {end - start} seconds")
    return answer


def generate_quiz(request):
    questions_data = request.session.get('questions', [])

    questions = []
    for q in questions_data:
        # Ensure q is a dictionary
        if isinstance(q, dict):
            question_text = q.get('question_text', 'No question text available')
            choices = q.get('choices', [])
            questions.append({'question_text': question_text, 'choices': choices})

    # Debug: Print questions to see what is being passed to the template
    print("Questions being passed to quiz page:", questions)

    return render(request, 'quiz.html', {'questions': questions})


def generate_questions(topic):
    try:
        # Call OpenAI API to generate questions and multiple choice answers
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Generate 10 quiz questions about {topic}, with four answer options (A, B, C, D), and indicate the correct answer."
            }]
        )

        # Debug: Log the API response
        print("API Response:", response)

        # Process response to create questions
        questions_text = response['choices'][0]['message']['content'].strip()
        questions_data = questions_text.split('\n\n') 
        questions = []
        
        for data in questions_data:
            if data.strip():
                # Split question text and answer options
                parts = data.split('\n')
                if len(parts) < 6:
                    continue  # Skip if the format is not correct

                question_text = parts[0].strip()
                options = [parts[i].strip() for i in range(1, 5)] 
                
                # Extract correct answer from the last line (like "Correct: A")
                correct_answer_line = parts[5].strip()  # Assuming the correct answer line follows the options
                correct_answer = correct_answer_line.split(':')[-1].strip()  # Get the part after "Correct: "

                questions.append({
                    'question_text': question_text,
                    'choices': options,
                    'answer': correct_answer  # Store the actual correct answer option (e.g., 'A')
                })

        # Debug: Log the generated questions
        print("Generated Questions:", questions)
        
        return questions

    except Exception as e:
        print("Error during question generation:", e)
        return []


def submit_quiz(request):
    questions = request.session.get('questions', [])
    score = 0
    total_questions = len(questions)
    results = []

    if request.method == 'POST':
        for idx, question in enumerate(questions):
            user_answer = request.POST.get(f'question_{idx}')
            correct_answer = question.get('answer')

            results.append({
                'question_number': idx + 1,  # Use question number (1-based index)
                'question_text': question.get('text'),  # Ensure this field exists
                'user_answer': user_answer,
                'correct_answer': correct_answer
            })

            if user_answer is not None and user_answer.strip() == correct_answer.strip():
                score += 1

        # Determine pass/fail status
        pass_threshold = total_questions / 2 
        passed = score > pass_threshold

        # Store results in the session
        request.session['quiz_results'] = results

        # Redirect to results view
        return redirect('results', score=score, total=total_questions, passed=passed)

    return redirect('generate_quiz')


def results(request, score, total, passed):
    passed = passed == 'True'  # Convert passed back to boolean if necessary
    results = request.session.get('quiz_results', [])

    return render(request, 'results.html', {
        'score': score,
        'total': total,
        'passed': passed,
        'results': results,
    })


def index(request):
    return render(request, 'index.html')


def voice_assistant_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        query = data.get("query", "").strip()  # Strip whitespace
        print(f"Received query: {query}")

        # Get response using OpenAI
        response = get_openai_response(query)
        speak(response)  # Optional: Use text-to-speech
        return JsonResponse({"response": response})
    return JsonResponse({"error": "Invalid request"}, status=400)


def get_openai_response(question):
    try:
        # Make the OpenAI API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or gpt-4 if you have access
            messages=[{"role": "user", "content": question}]
        )
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        print(f"Error contacting OpenAI: {e}")
        return "Sorry, I couldn't get an answer for that."


def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


#Scanning 
def create_pdf_from_image(image_data, pdf_path):
    """Convert the captured image to PDF."""
    
    # Clean base64 image data
    image_data_cleaned = re.sub(r'^data:image/.+;base64,', '', image_data)
    padding = len(image_data_cleaned) % 4
    if padding:
        image_data_cleaned += '=' * (4 - padding)

    try:
        # Decode base64 to image bytes
        image_bytes = base64.b64decode(image_data_cleaned)

        # Open image using PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Save image to a temporary file to use for PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_image_file:
            tmp_image_path = tmp_image_file.name
            image.save(tmp_image_path)

        # Create PDF with image embedded
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf_file:
            tmp_pdf_path = tmp_pdf_file.name
            c = canvas.Canvas(tmp_pdf_path, pagesize=(image.width, image.height))
            c.drawImage(tmp_image_path, 0, 0, width=image.width, height=image.height)
            c.save()

        return tmp_pdf_path

    except Exception as e:
        raise ValueError(f"Error creating PDF: {str(e)}")

def extract_text_from_pdf(pdf_path):
    """Extract text from the PDF using PyMuPDF and apply OCR if necessary."""
    doc = fitz.open(pdf_path)
    extracted_text = ""

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Try extracting text first
        page_text = page.get_text("text")
        extracted_text += page_text

        # If the text extraction is empty, apply OCR on images in the PDF
        if not page_text.strip():
            # Extract images from the page
            images = page.get_images(full=True)
            for img in images:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))

                # Apply OCR on the image
                extracted_text += pytesseract.image_to_string(image)

    return extracted_text

def preprocess_image(image):
    """Preprocess the image to improve OCR accuracy."""
    # Convert image to grayscale
    image = image.convert('L')

    # Apply thresholding to binarize the image (black and white)
    image = image.point(lambda p: p > 200 and 255)

    # Optionally, apply additional image processing (e.g., noise removal)
    image = image.filter(ImageFilter.MedianFilter())

    return image

def solution_capture_view(request):
    """Main view to handle solution upload and processing."""
    if request.method == 'POST':
        form = SolutionForm(request.POST, request.FILES)
        if form.is_valid():
            solution = form.save()

            # Extract text from the uploaded image
            extracted_text = extract_text_from_image(solution.image.path)
            solution.extracted_text = extracted_text

            # Evaluate the solution
            evaluation = evaluate_solution(extracted_text)
            solution.is_correct = "correct" in evaluation.lower()

            # Provide steps for the solution
            steps = provide_steps(extracted_text)
            solution.solution_step = steps

            # Save solution
            solution.save()

            return redirect('edit_solution', solution.id)

        return process_image(request)

    else:
        form = SolutionForm()

    return render(request, 'capture_solution.html', {'form': form})

def extract_text_from_image(image_data):
    """Extract text from the base64-encoded image with improved settings for handwriting."""
    # Remove the base64 prefix if it exists
    image_data = image_data.split(',')[1]
    image_bytes = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(image_bytes))

    # Preprocess the image for better OCR accuracy
    image = preprocess_image_for_handwriting(image)

    # Use custom OCR config to improve recognition of handwritten text
    custom_config = r'--oem 3 --psm 6'  # OEM 3 (default), PSM 6 (assumes a uniform block of text)
    
    # Tesseract OCR with the new config and image preprocessing
    extracted_text = pytesseract.image_to_string(image, config=custom_config)
    
    return extracted_text

def preprocess_image_for_handwriting(image):
    """Preprocess the image to improve OCR accuracy for handwriting."""
    # Convert image to grayscale
    image = image.convert('L')

    # Apply contrast enhancement (increases the difference between ink and paper)
    image = ImageEnhance.Contrast(image).enhance(2)

    # Convert image to numpy array for OpenCV processing
    img_np = np.array(image)

    # Apply adaptive thresholding (better for uneven lighting)
    img_thresholded = cv2.adaptiveThreshold(
        img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Convert back to PIL image
    image = Image.fromarray(img_thresholded)

    # Optionally, apply additional noise reduction filters
    image = image.filter(ImageFilter.MedianFilter())

    return image

def extract_text_from_image_openai(image_data):
    """Extract text from an image using OpenAI GPT-4's image processing capabilities (future support)."""
    try:
        # Convert base64 string to image bytes
        image_bytes = base64.b64decode(image_data.split(',')[1])

        # Make an API call to OpenAI's GPT-4 with image input (assuming access to the image input API)
        response = openai.Image.create(
            prompt="Extract text from the image.",
            images=[{"image": image_bytes}],
        )

        # Check for text in the response and return it
        if 'text' in response:
            return response['text']
        else:
            return ""  # Return empty string if no text is found in the response
    except Exception as e:
        print(f"Error extracting text from image using OpenAI: {e}")
        return ""  # Return empty string in case of an error

def process_image(request):
    """Process the captured image and extract text."""
    if request.method == 'POST':
        image_data = request.POST.get('image_data')

        if not image_data:
            raise ValueError("No image data received in the request")

        # First, attempt to extract text with Tesseract OCR
        extracted_text = extract_text_from_image(image_data)

        # Check if Tesseract found sufficient text; otherwise, use OpenAI (or fallback)
        if not extracted_text.strip():
            # Optionally use other services or retry with different OCR configurations
            extracted_text = extract_text_from_image_openai(image_data)

        # Evaluate the solution using OpenAI or other logic
        evaluation = evaluate_solution(extracted_text)

        # Provide steps for the solution
        steps = provide_steps(extracted_text)

        # Create a new solution object and save the extracted text, evaluation, and steps
        solution = Solution.objects.create(
            extracted_text=extracted_text,
            is_correct="correct" in evaluation.lower(),
            solution_step=steps
        )

        # Redirect to the edit page where the user can modify the extracted text
        return redirect('edit_solution', solution_id=solution.id)

    return redirect('capture_solution')

def evaluate_solution(extracted_text):
    """Use OpenAI's chat model to evaluate if the solution is correct."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Correct model
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": f"Evaluate if this solution is correct: {extracted_text}"}]
    )
    return response['choices'][0]['message']['content'].strip()

def provide_steps(extracted_text):
    """Provide detailed steps to solve the given problem using OpenAI's chat model."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Correct model
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": f"Provide detailed steps to solve the following: {extracted_text}"}]
    )
    return response['choices'][0]['message']['content'].strip()

def edit_solution(request, solution_id):
    """Allow user to edit the extracted text and evaluate again."""
    solution = Solution.objects.get(id=solution_id)

    if request.method == 'POST':
        solution.user_edited_text = request.POST['user_edited_text']

        # Reevaluate the solution based on the edited text
        evaluation = evaluate_solution(solution.user_edited_text)
        solution.is_correct = "correct" in evaluation.lower()

        # Provide steps for the solution
        steps = provide_steps(solution.user_edited_text)
        solution.solution_step = steps

        solution.save()

        return redirect('solution_detail', solution_id=solution.id)

    return render(request, 'edit_solution.html', {'solution': solution})

def solution_detail(request, solution_id):
    """Show details of the solution."""
    solution = Solution.objects.get(id=solution_id)
    return render(request, 'detail.html', {'solution': solution})
