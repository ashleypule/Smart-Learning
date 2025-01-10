from django import forms
from .models import Solution

class DocumentUploadForm(forms.Form):
    document = forms.FileField()


class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField()
    num_questions = forms.IntegerField(min_value=1)
    difficulty_level = forms.ChoiceField(choices=[("Easy", "Easy"), ("Medium", "Medium"), ("Hard", "Hard")])


class TopicForm(forms.Form):
    topic = forms.CharField(label='Enter Topic', max_length=100)

class QuizForm(forms.Form):
    def __init__(self, questions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for idx, question in enumerate(questions):
            self.fields[f'question_{idx}'] = forms.ChoiceField(
                label=question['question_text'],
                choices=[(choice, choice) for choice in question['choices']],
                widget=forms.RadioSelect
            )

class SolutionForm(forms.ModelForm):
    class Meta:
        model = Solution
        fields = ['image', 'user_edited_text']

class EssayForm(forms.Form):
    essay_text = forms.CharField(widget=forms.Textarea)