# Multi-Dimensional Reflection Cycle Recommender System

An intelligent ticket recommendation system based on large language models, implementing high-quality personalized recommendations for flights and train tickets through a reflection cycle mechanism. The system can analyze user needs, self-evaluate recommendation quality, and continuously optimize recommendation results.

## System Features

- **Multi-dimensional Evaluation**: Assesses recommendation quality from three dimensions: needs matching, completeness of options, and practicality
- **Reflection Cycle Mechanism**: Continuously optimizes recommendation results through self-reflection
- **Personalized Recommendations**: Deeply understands users' explicit and implicit needs to provide customized recommendations

## System Architecture

- **Core Modules**:

  - Reflection Engine (ReflectionEngine)
  - Data Processor (DataProcessor)
  - Recommendation Evaluator (RecommendationEvaluator)
  - LLM Client (LLMClient)

- **Data Models**:

  - User Needs Model (UserNeeds)
  - Ticket Data Model (TicketData)
  - Recommendation Result Model (Recommendation)

- **API Interface**: Asynchronous Web API based on Sanic

## Quick Start

### Requirements

- Python 3.8+
- Configured OpenAI API key

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configuration

1. Create a `.env` file, refer to `.env.example` to add necessary configurations

### Run Examples

```bash
# Run the demo example
python examples/recommendation_demo.py

# Start the web service
python main.py
```

## API Endpoints

### Create Recommendation

```
POST /api/v1/recommendations
```

Request body:

```json
{
  "conversation_text": "I want to travel from Beijing to Shanghai next Friday, with a budget within 1000 yuan, preferably by high-speed rail"
}
```

### Get Recommendation

```
GET /api/v1/recommendations/{recommendation_id}
```

### Reflect and Optimize Recommendation

```
POST /api/v1/recommendations/{recommendation_id}/reflect
```

Request body:

```json
{
  "feedback": "I prefer afternoon trips, and it would be better if it's cheaper"
}
```

## Extension and Customization

The system is designed to be highly extensible and can be customized in the following ways:

1. Implement your own data source interface
2. Adjust scoring model parameters
3. Customize reflection logic and prompts
4. Use different large language models

## License

MIT
