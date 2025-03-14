import ollama

try:
    response = ollama.chat(model="llama3.2:3b", messages=[{"role": "user", "content": "Hello, Ollama!"}])
    
    print("Response Type:", type(response))
    print("Response:", response)

except Exception as e:
    print("Ollama Test Error:", e)