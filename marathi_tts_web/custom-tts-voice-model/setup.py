from setuptools import setup, find_packages

setup(
    name='custom-tts-voice-model',
    version='0.1.0',
    author='Marathi TTS Contributors',
    description='A custom voice model for text-to-speech using open-source Python libraries.',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'pandas',
        'scipy',
        'librosa',
        'tensorflow',  # or 'torch' depending on the model framework
        'matplotlib',
        'jupyter'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)