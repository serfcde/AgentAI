from my_crew.workflows.workflow_router import choose_workflow


def main():

    topic = input("Enter Topic: ")

    result = choose_workflow(topic)

    print(result)


if __name__ == "__main__":
    main()
