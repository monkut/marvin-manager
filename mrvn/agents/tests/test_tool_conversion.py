"""Tests for tool definition conversion to provider-specific formats."""

from django.test import TestCase

from agents.tools import ToolRegistry
from agents.tools.builtin import CalculatorTool, DateTimeTool


class ToolConversionTests(TestCase):
    """Tests for tool format conversion."""

    def setUp(self) -> None:
        """Set up test registry with tools."""
        self.registry = ToolRegistry()
        self.registry.register(CalculatorTool())
        self.registry.register(DateTimeTool())

    def test_to_anthropic_format_structure(self) -> None:
        """Verify Anthropic format has name, description, input_schema."""
        tools = self.registry.to_anthropic_tools()

        self.assertEqual(len(tools), 2)
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("input_schema", tool)
            self.assertIsInstance(tool["input_schema"], dict)
            self.assertIn("type", tool["input_schema"])
            self.assertEqual(tool["input_schema"]["type"], "object")

    def test_to_anthropic_format_calculator(self) -> None:
        """Verify Calculator tool converts correctly to Anthropic format."""
        tools = self.registry.to_anthropic_tools()
        calculator = next(t for t in tools if t["name"] == "calculator")

        self.assertEqual(calculator["name"], "calculator")
        self.assertIn("properties", calculator["input_schema"])
        self.assertIn("expression", calculator["input_schema"]["properties"])
        self.assertIn("required", calculator["input_schema"])
        self.assertIn("expression", calculator["input_schema"]["required"])

    def test_to_anthropic_format_datetime(self) -> None:
        """Verify DateTime tool converts correctly to Anthropic format."""
        tools = self.registry.to_anthropic_tools()
        datetime_tool = next(t for t in tools if t["name"] == "get_datetime")

        self.assertEqual(datetime_tool["name"], "get_datetime")
        self.assertIn("properties", datetime_tool["input_schema"])
        self.assertIn("timezone", datetime_tool["input_schema"]["properties"])
        self.assertIn("output_format", datetime_tool["input_schema"]["properties"])

    def test_to_openai_format_structure(self) -> None:
        """Verify OpenAI format wraps in function object."""
        tools = self.registry.to_openai_tools()

        self.assertEqual(len(tools), 2)
        for tool in tools:
            self.assertIn("type", tool)
            self.assertEqual(tool["type"], "function")
            self.assertIn("function", tool)
            self.assertIn("name", tool["function"])
            self.assertIn("description", tool["function"])
            self.assertIn("parameters", tool["function"])

    def test_to_openai_format_calculator(self) -> None:
        """Verify Calculator tool converts correctly to OpenAI format."""
        tools = self.registry.to_openai_tools()
        calculator = next(t for t in tools if t["function"]["name"] == "calculator")

        func = calculator["function"]
        self.assertEqual(func["name"], "calculator")
        self.assertIn("parameters", func)
        self.assertIn("properties", func["parameters"])
        self.assertIn("expression", func["parameters"]["properties"])
        self.assertEqual(func["parameters"]["properties"]["expression"]["type"], "string")

    def test_to_openai_format_datetime_enum(self) -> None:
        """Verify DateTime tool enum parameter converts correctly."""
        tools = self.registry.to_openai_tools()
        datetime_tool = next(t for t in tools if t["function"]["name"] == "get_datetime")

        params = datetime_tool["function"]["parameters"]
        output_format = params["properties"]["output_format"]
        self.assertIn("enum", output_format)
        self.assertIn("iso", output_format["enum"])
        self.assertIn("human", output_format["enum"])

    def test_to_gemini_format_structure(self) -> None:
        """Verify Gemini format has name, description, parameters per tool."""
        tools = self.registry.to_gemini_tools()

        # Gemini format returns individual tool definitions (not wrapped)
        self.assertEqual(len(tools), 2)
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("parameters", tool)

    def test_to_gemini_format_calculator(self) -> None:
        """Verify Calculator tool converts correctly to Gemini format."""
        tools = self.registry.to_gemini_tools()
        calculator = next(t for t in tools if t["name"] == "calculator")

        self.assertEqual(calculator["name"], "calculator")
        self.assertIn("parameters", calculator)
        self.assertIn("properties", calculator["parameters"])
        self.assertIn("expression", calculator["parameters"]["properties"])

    def test_filter_tools_by_name(self) -> None:
        """Verify tools can be filtered by name."""
        # Anthropic format
        tools = self.registry.to_anthropic_tools(tool_names=["calculator"])
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "calculator")

        # OpenAI format
        tools = self.registry.to_openai_tools(tool_names=["get_datetime"])
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["function"]["name"], "get_datetime")

        # Gemini format
        tools = self.registry.to_gemini_tools(tool_names=["calculator"])
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "calculator")

    def test_empty_registry_returns_empty_list(self) -> None:
        """Verify empty registry returns empty lists."""
        empty_registry = ToolRegistry()

        self.assertEqual(empty_registry.to_anthropic_tools(), [])
        self.assertEqual(empty_registry.to_openai_tools(), [])
        self.assertEqual(empty_registry.to_gemini_tools(), [])
