from my_crew.workflows.network_flow import run_network_flow


def main():

    result = run_network_flow()

    print("\nFINAL RESULT:\n")

    print(result)


if __name__ == "__main__":
    main()