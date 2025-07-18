# tools/deep_research/tests/mocks.py

import json
from event_management.event_emitter import EventEmitter

NODE_START_EVENT_JSON = json.dumps({
  "type": "node_start",
  "content": {
    "id": "889086f0-9f89-41c2-8868-4cf73ff0727c",
    "node_id": "1739253994297",
    "node_type": "answer",
    "title": "Answer",
    "index": 27,
    "predecessor_node_id": "1739254296073",
    "inputs": None,
    "created_at": 1752771347,
    "extras": {},
    "parallel_id": None,
    "parallel_start_node_id": None,
    "parent_parallel_id": None,
    "parent_parallel_start_node_id": None,
    "iteration_id": "1739244888446",
    "loop_id": None,
    "parallel_run_id": None,
    "agent_strategy": None
  }
})

ITERATION_FINISH_EVENT_JSON = json.dumps({
  "type": "iteration_finish",
  "content": {
    "id": "1739244888446",
    "node_id": "1739244888446",
    "node_type": "iteration",
    "title": "Iteration",
    "outputs": {
      "output": [
        " ",
        " ",
        " "
      ]
    },
    "created_at": 1752771347,
    "extras": {},
    "inputs": {
      "iterator_selector": [
        0,
        1,
        2
      ]
    },
    "status": "succeeded",
    "error": None,
    "elapsed_time": 11.989818,
    "total_tokens": 1987,
    "execution_metadata": {
      "total_tokens": 1987
    },
    "finished_at": 1752771347,
    "steps": 3,
    "parallel_id": None,
    "parallel_start_node_id": None
  }
})

NODE_FINISH_VARIABLE_AGGREGATOR_JSON = json.dumps({
  "type": "node_finish",
  "content": {
    "id": "89698a66-dc28-4f94-9ed1-93e281abe8fe",
    "node_id": "1739254296073",
    "node_type": "variable-aggregator",
    "title": "Variable Aggregator",
    "index": 26,
    "predecessor_node_id": "1739254516383",
    "inputs": {
      "output": " "
    },
    "process_data": None,
    "outputs": {
      "output": " "
    },
    "status": "succeeded",
    "error": None,
    "elapsed_time": 0.009482,
    "execution_metadata": {
      "iteration_id": "1739244888446",
      "iteration_index": 2
    },
    "created_at": 1752771347,
    "finished_at": 1752771347,
    "files": [],
    "parallel_id": None,
    "parallel_start_node_id": None,
    "parent_parallel_id": None,
    "parent_parallel_start_node_id": None,
    "iteration_id": "1739244888446",
    "loop_id": None
  }
})

NODE_START_VARIABLE_AGGREGATOR_JSON = json.dumps({
  "type": "node_start",
  "content": {
    "id": "89698a66-dc28-4f94-9ed1-93e281abe8fe",
    "node_id": "1739254296073",
    "node_type": "variable-aggregator",
    "title": "Variable Aggregator",
    "index": 26,
    "predecessor_node_id": "1739254516383",
    "inputs": None,
    "created_at": 1752771347,
    "extras": {},
    "parallel_id": None,
    "parallel_start_node_id": None,
    "parent_parallel_id": None,
    "parent_parallel_start_node_id": None,
    "iteration_id": "1739244888446",
    "loop_id": None,
    "parallel_run_id": None,
    "agent_strategy": None
  }
})

NODE_FINISH_TEMPLATE_TRANSFORM_JSON = json.dumps({
  "type": "node_finish",
  "content": {
    "id": "bdb05db5-58d8-499f-ab03-dd9fd75c03a9",
    "node_id": "1739254516383",
    "node_type": "template-transform",
    "title": "Empty",
    "index": 25,
    "predecessor_node_id": "1739245723720",
    "inputs": None,
    "process_data": None,
    "outputs": {
      "output": " "
    },
    "status": "succeeded",
    "error": None,
    "elapsed_time": 0.098565,
    "execution_metadata": {
      "iteration_id": "1739244888446",
      "iteration_index": 2
    },
    "created_at": 1752771347,
    "finished_at": 1752771347,
    "files": [],
    "parallel_id": None,
    "parallel_start_node_id": None,
    "parent_parallel_id": None,
    "parent_parallel_start_node_id": None,
    "iteration_id": "1739244888446",
    "loop_id": None
  }
})

NODE_FINISH_IF_ELSE_JSON = json.dumps({
  "type": "node_finish",
  "content": {
    "id": "7f9e37b4-0db1-4f59-9c2a-26405fac0a50",
    "node_id": "1739245723720",
    "node_type": "if-else",
    "title": "IF/ELSE",
    "index": 24,
    "predecessor_node_id": "1739245826988",
    "inputs": {
      "conditions": [
        {
          "actual_value": "Expecting value: line 1 column 1 (char 0)",
          "expected_value": "True",
          "comparison_operator": "is"
        }
      ]
    },
    "process_data": {
      "condition_results": [
        {
          "group": {
            "case_id": "true",
            "logical_operator": "and",
            "conditions": [
              {
                "variable_selector": [
                  "1739245524260",
                  "text"
                ],
                "comparison_operator": "is",
                "value": "True",
                "sub_variable_condition": None
              }
            ]
          },
          "results": [
            False
          ],
          "final_result": False
        }
      ]
    },
    "outputs": {
      "result": False,
      "selected_case_id": None
    },
    "status": "succeeded",
    "error": None,
    "elapsed_time": 0.039228,
    "execution_metadata": {
      "iteration_id": "1739244888446",
      "iteration_index": 2
    },
    "created_at": 1752771347,
    "finished_at": 1752771347,
    "files": [],
    "parallel_id": None,
    "parallel_start_node_id": None,
    "parent_parallel_id": None,
    "parent_parallel_start_node_id": None,
    "iteration_id": "1739244888446",
    "loop_id": None
  }
})

NODE_FINISH_LLM_JSON = json.dumps({
  "type": "node_finish",
  "content": {
    "id": "337cf8a7-0f0b-45c3-9e57-eef11010fe2b",
    "node_id": "1739246156652",
    "node_type": "llm",
    "title": "Reasoning Model",
    "index": 28,
    "predecessor_node_id": "1739244888446",
    "inputs": None,
    "process_data": {
      "model_mode": "chat",
      "prompts": [
        {
          "role": "system",
          "text": "  Based on the investigation results, create a comprehensive analysis of the topic.\\nProvide important insights, conclusions, and remaining uncertainties. Cite sources where appropriate. This analysis should be very comprehensive and detailed. It is expected to be a long text.\\n\\n## Topic\\nresearch about cat memes\\n\\n## Findings \\n[]\\n",
          "files": []
        },
        {
          "role": "user",
          "text": "## topic\\nresearch about cat memes\\n\\n# findings \\n[]\\n",
          "files": []
        }
      ],
      "model_provider": "langgenius/ollama/ollama",
      "model_name": "deepseek-r1"
    },
    "outputs": {
      "text": "<think>\nAlright, so I need to figure out how to approach this query where the user wants an analysis of research about cat memes. The initial response they got was a comprehensive breakdown with sections like Introduction, Literature Review, Findings, and Conclusions. But since the user is asking for a detailed analysis now, maybe they want more in-depth information or perhaps additional insights beyond what's already provided.\n\nFirst, I should assess why the user needs this analysis. They mentioned it's expected to be long and comprehensive, so they might be an academic researcher, student, or someone compiling information for an article or presentation. Their deeper need could be to understand not just what's been studied about cat memes but also how that research contributes to broader fields like digital culture or psychology.\n\nI should check if the user has provided specific findings yet. The initial query had a response without any findings listed inside the brackets, so perhaps they want me to expand on an existing structure rather than starting from scratch. Maybe they need more detailed sections under each point, such as subcategories within the literature review or expanded analysis of each finding.\n\nLooking at the previous response, it was well-structured but could be extended with additional data points, statistics, or recent studies that have come to light since then. For instance, including information on how AI is influencing cat meme culture would add depth and show current trends.\n\nI should also consider if there are any emerging trends or future research directions the user might be interested in. This could provide a forward-looking perspective, making the analysis more useful for planning further studies or writing papers.\n\nAdditionally, I need to ensure that all sources are properly cited throughout the analysis to maintain credibility and avoid plagiarism. Including recent publications will also keep the information up-to-date.\n\nI should verify if there are any gaps in the current research that could be filled by future studies. This might involve looking into how cat memes intersect with other cultural forms or their impact on mental health beyond the previously mentioned points.\n\nOverall, my approach would be to expand each section with more detailed analysis, include recent data and examples, and ensure all citations are correctly referenced. I'll also make sure to highlight both established findings and emerging trends to provide a thorough and forward-looking analysis.\n</think>\n\n### Comprehensive Analysis of Research About Cat Memes\n\nCat memes have become a fascinating subject of study due ...",
      "usage": {
        "prompt_tokens": 84,
        "prompt_unit_price": "0",
        "prompt_price_unit": "0",
        "prompt_price": "0",
        "completion_tokens": 2116,
        "completion_unit_price": "0",
        "completion_price_unit": "0",
        "completion_price": "0",
        "total_tokens": 2200,
        "total_price": "0",
        "currency": "USD",
        "latency": 15.050241325050592
      },
      "finish_reason": "stop"
    },
    "status": "succeeded",
    "error": None,
    "elapsed_time": 15.085455,
    "execution_metadata": {
      "total_tokens": 2200,
      "total_price": "0",
      "currency": "USD"
    },
    "created_at": 1752771347,
    "finished_at": 1752771362,
    "files": [],
    "parallel_id": None,
    "parallel_start_node_id": None,
    "parent_parallel_id": None,
    "parent_parallel_start_node_id": None,
    "iteration_id": None,
    "loop_id": None
  }
})

WORKFLOW_FINISH_EVENT_JSON = json.dumps({
  "type": "workflow_finish",
  "content": {
    "id": "35ef4ccf-c111-4f50-9732-08c324c002e2",
    "workflow_id": "f2f20deb-4b6f-4edd-b08a-c20538aeb204",
    "sequence_number": 120,
    "status": "succeeded",
    "outputs": {
      "answer": "<think>\nAlright, so I need to figure out how to approach this query where the user wants an analysis of research about cat memes. The initial response they got was a comprehensive breakdown with sections like Introduction, Literature Review, Findings, and Conclusions. But since the user is asking for a detailed analysis now, maybe they want more in-depth information or perhaps additional insights beyond what's already provided.\n\nFirst, I should assess why the user needs this analysis. They mentioned it's expected to be long and comprehensive, so they might be an academic researcher, student, or someone compiling information for an article or presentation. Their deeper need could be to understand not just what's been studied about cat memes but also how that research contributes to broader fields like digital culture or psychology.\n\nI should check if the user has provided specific findings yet. The initial query had a response without any findings listed inside the brackets, so perhaps they want me to expand on an existing structure rather than starting from scratch. Maybe they need more detailed sections under each point, such as subcategories within the literature review or expanded analysis of each finding.\n\nLooking at the previous response, it was well-structured but could be extended with additional data points, statistics, or recent studies that have come to light since then. For instance, including information on how AI is influencing cat meme culture would add depth and show current trends.\n\nI should also consider if there are any emerging trends or future research directions the user might be interested in. This could provide a forward-looking perspective, making the analysis more useful for planning further studies or writing papers.\n\nAdditionally, I need to ensure that all sources are properly cited throughout the analysis to maintain credibility and avoid plagiarism. Including recent publications will also keep the information up-to-date.\n\nI should verify if there are any gaps in the current research that could be filled by future studies. This might involve looking into how cat memes intersect with other cultural forms or their impact on mental health beyond the previously mentioned points.\n\nOverall, my approach would be to expand each section with more detailed analysis, include recent data and examples, and ensure all citations are correctly referenced. I'll also make sure to highlight both established findings and emerging trends to provide a thorough and forward-looking analysis.\n</think>\n\n### Comprehensive Analysis of Research About Cat Memes\n\nCat memes have become a fascinating subject of study due ..."
    },
    "error": None,
    "elapsed_time": 27.15746214997489,
    "total_tokens": 4187,
    "total_steps": 29,
    "created_by": {
      "id": "0eba4b4b-c8d1-4dac-9874-948e117d0767",
      "user": "test@example.com"
    },
    "created_at": 1752771335,
    "finished_at": 1752771362,
    "exceptions_count": 0,
    "files": []
  }
})


class MockEventEmitter(EventEmitter):
    def __init__(self, request_info_data):
        self._request_info = request_info_data # The data to be captured

    async def __call__(self, event_data):
        # In a real Open WebUI environment, this would send an event to the UI
        print(f"Emitting event: {event_data}")
        return event_data

    @property
    def __closure__(self):
        # This is where the magic happens for demonstration
        # In a real scenario, the __closure__ would be naturally created
        # if MockEventEmitter was a nested function or had a cell object
        # for _request_info. For demonstration, we're simulating it.
        class Cell:
            def __init__(self, content):
                self.cell_contents = content
        return (Cell(self._request_info),)
