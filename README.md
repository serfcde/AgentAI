# Production-Style CrewAI Multi-Agent Workflow

This project demonstrates a modular CrewAI workflow with five agents, seven tools,
basic Agent2Agent-style communication, and separate workflow pattern examples for
network, hierarchical, and parallel orchestration.

The current executable entry point runs the network workflow:

```text
Research Agent -> Planning Agent -> Execution Agent -> Validation Agent
```

The workflow uses an Ollama-backed local LLM by default.

## Project Structure

```text
.
├── src/my_crew/
│   ├── a2a/                  # Agent-to-agent message objects and bus
│   ├── agents/               # CrewAI agent factories
│   ├── config/               # Agent and task YAML configuration
│   ├── tasks/                # CrewAI task factories
│   ├── tools/                # CrewAI tool definitions
│   ├── workflows/            # Network, hierarchical, and parallel flows
│   ├── crew.py               # Crew factory
│   └── main.py               # Main executable entry point
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Agents

The system defines five CrewAI agents:

- `Research Agent`: gathers research and source context.
- `Planning Agent`: decomposes objectives into execution plans.
- `Execution Agent`: produces actionable implementation output.
- `Validation Agent`: reviews generated output for quality and consistency.
- `Supervisor Agent`: supports hierarchical orchestration and delegation.

## Tools

The project includes seven tool modules:

- `Web Search Tool`
- `File Reader Tool`
- `Memory Tool`
- `Logger Tool`
- `Calculator Tool`
- `Notification Tool`
- `API Tool`

Some tools are deterministic local helpers, while the API tool performs real HTTP
requests.

## Workflow Patterns

### Network Pattern

Implemented in `src/my_crew/workflows/network_flow.py`.

```text
Research
   |
   v
Planning
   |
   v
Execution
   |
   v
Validation
   |
   +-- optional improvement loop --> Research
```

### Hierarchical Pattern

Implemented in `src/my_crew/workflows/hierarchical_flow.py`.

```text
Supervisor Agent
   |
   +--> Research Agent
   +--> Planning Agent
   +--> Execution Agent
   +--> Validation Agent
```

### Parallel Pattern

Implemented in `src/my_crew/workflows/parallel_flow.py`.

```text
        +--> Research Flow ----+
Topic --+--> Planning Flow ----+--> Combined result
        +--> Execution Flow ---+
```

## A2A Communication

The `src/my_crew/a2a/` package contains:

- `AgentMessage`: a simple message envelope with sender, receiver, and content.
- `A2AProtocol`: message validation and JSON serialization helpers.
- `CommunicationBus`: an in-memory bus used by the network flow to pass outputs
  between agents.

This is a lightweight local A2A layer suitable for demonstrating inter-agent
communication inside the project architecture.

## Local Setup

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

Start Ollama and pull the configured model:

```bash
ollama serve
ollama pull llama3.1
```

Run the workflow:

```bash
python -m my_crew.main
```

## Docker Setup

Build the application image:

```bash
docker compose build
```

Start Ollama:

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.1
```

Run the app:

```bash
docker compose run --rm app
```

## Development Checks

Compile the source tree:

```bash
python -m compileall src/my_crew
```

Run the executable workflow:

```bash
python -m my_crew.main
```

## Notes

- The default LLM configuration is in `src/my_crew/config/llm.py`.
- The current main entry point runs the network workflow.
- The hierarchical and parallel workflow implementations are available as
  importable functions and can be wired into a CLI selector later.
