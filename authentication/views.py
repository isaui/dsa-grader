from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

def register_view(request):
    if request.user.is_authenticated:
        return redirect('main:problem_list')
        
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Langsung login setelah register
            login(request, user)
            return redirect('main:problem_list')
    else:
        form = UserCreationForm()
    
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('main:problem_list')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Redirect ke halaman yang diminta sebelum login jika ada
                next_page = request.GET.get('next', 'main:problem_list')
                return redirect(next_page)
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('authentication:login')