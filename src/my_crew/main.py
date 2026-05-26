from my_crew.crew import create_ai_crew


def main():

    topic = "Future of AI Agents"

    crew = create_ai_crew(topic)

    result = crew.kickoff()

    print("\n\nFINAL RESULT:\n")
    print(result)


if __name__ == "__main__":
    main()