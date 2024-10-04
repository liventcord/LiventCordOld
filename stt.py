import torch
from transformers import pipeline

device = "cuda:0" if torch.cuda.is_available() else "cpu"

pipe = pipeline(
  "automatic-speech-recognition",
  model="openai/whisper-medium.en",
  chunk_length_s=30,
  device=device,
)
transcription = pipe("preamble.wav")['text']
print(transcription)