import datetime
import os
import subprocess
import uuid
import re


def compile_code(submission, language, temp_dir):
    """Compile code with safe filename handling"""
    # Generate unique directory name for this submission
    safe_dirname = generate_safe_dirname(submission, language)
    submission_dir = os.path.join(temp_dir, safe_dirname)
    os.makedirs(submission_dir, exist_ok=True)
    
    compilation_result = {
        'success': False,
        'message': '',
        'filename': safe_dirname  # untuk reference di grader
    }
    
    try:
        if language == 'python':
            # For Python, we can use the safe dirname as the module name
            source_file = os.path.join(submission_dir, 'solution.py')
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(submission.code)
            compilation_result['success'] = True
            
        elif language == 'java':
            # For Java, we must use the public class name as the file name
            main_class = extract_java_class_name(submission.code)
            if not main_class:
                compilation_result['message'] = "Could not find main class name in Java code"
                return compilation_result
            
            # Write Java code with original class name
            source_file = os.path.join(submission_dir, f"{main_class}.java")
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(submission.code)
            
            # Compile Java code
            proc = subprocess.run(
                ['javac', source_file], 
                capture_output=True, 
                text=True,
                cwd=submission_dir  # Compile in submission directory
            )
            
            if proc.returncode == 0:
                compilation_result['success'] = True
                compilation_result['main_class'] = main_class  # Save for execution
            else:
                compilation_result['message'] = proc.stderr
                
        elif language in ['c', 'cpp']:
            # For C/C++, use standard names
            ext = '.c' if language == 'c' else '.cpp'
            compiler = 'gcc' if language == 'c' else 'g++'
            source_file = os.path.join(submission_dir, f"solution{ext}")
            output_file = os.path.join(submission_dir, "solution")
            
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(submission.code)
            
            proc = subprocess.run(
                [compiler, source_file, '-o', output_file],
                capture_output=True,
                text=True,
                cwd=submission_dir
            )
            
            if proc.returncode == 0:
                compilation_result['success'] = True
            else:
                compilation_result['message'] = proc.stderr
                
    except Exception as e:
        compilation_result['message'] = str(e)
        
    return compilation_result

def generate_safe_dirname(submission, language):
    """Generate unique and safe directory name for submission"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    
    dirname = f"{submission.id}_{submission.user.id}_{submission.problem.id}_{timestamp}_{unique_id}"
    safe_dirname = "".join(c for c in dirname if c.isalnum() or c in ('_', '-'))
    
    return safe_dirname

def extract_java_class_name(code):
    """Extract main class name from Java code"""
    # Must find public class for Java
    match = re.search(r'public\s+class\s+(\w+)', code)
    if not match:
        return None
    return match.group(1)
