# al-assessment

## Requirements
- Python 3.12 or higher
- `pip` (Python's package manager)

## Installation

### 1. Clone the repository:
Clone the project to your local machine:
```bash
git clone https://github.com/syuu1208/al-assessment.git
cd al-assessment
```

### 2. Install the required libraries listed in requirements.txt:
```
pip install -r requirements.txt
```

### 3. Run the main script:
```
python assessment.py
```


Additional notes:
The assignment requested to use committer object when pulling commits from the API call; however, all commiter objects had 'login' object of the same name ('web-flow'), which will cause top committers and longest streak to be of user 'web-flow'. Hence, we will be using the author object to differentiate the users.

Sample image:

![image](https://github.com/user-attachments/assets/9fcefc47-7810-4619-90b2-1dd98d9aa9b6)
