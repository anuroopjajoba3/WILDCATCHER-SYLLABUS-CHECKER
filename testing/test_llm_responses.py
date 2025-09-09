from backend_switch import get_backend

def main():
    # Load backend (OpenAI or OSS based on .env or override)
    models = get_backend()

    # Prompts to test
    prompts = [
        "What is the capital of France?",
        "Tell me a fun fact about space.",
        "What is 15 times 12?",
        "Summarize the plot of Romeo and Juliet.",
    ]

    print(f"Testing LLM with backend: {models.name}")
    print("-" * 40)

    for prompt in prompts:
        try:
            # Some models use .invoke() or __call__(), adjust if needed
            response = models.llm.invoke(prompt)
            print(f"Prompt: {prompt}")
            print("Response:", response.content if hasattr(response, "content") else response)
            print("-" * 40)
        except Exception as e:
            print(f"Error for prompt '{prompt}':", e)

if __name__ == "__main__":
    main()
