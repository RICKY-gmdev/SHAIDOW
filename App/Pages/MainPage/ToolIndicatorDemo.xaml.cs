using Microsoft.Maui.Controls;

namespace App
{
    public partial class ToolIndicatorDemo : ContentPage
    {
        private readonly List<string> _demoTools = new() { "mistral", "claude", "gpt", "web_search", "file_search" };
        private int _currentToolIndex = 0;

        public ToolIndicatorDemo()
        {
            InitializeComponent();
        }

        private void OnShowMistralClicked(object sender, EventArgs e)
        {
            DemoToolIndicator.ClearAllTools();
            DemoToolIndicator.ShowTool("mistral");
        }

        private void OnShowClaudeClicked(object sender, EventArgs e)
        {
            DemoToolIndicator.ClearAllTools();
            DemoToolIndicator.ShowTool("claude");
        }

        private void OnShowGPTClicked(object sender, EventArgs e)
        {
            DemoToolIndicator.ClearAllTools();
            DemoToolIndicator.ShowTool("gpt");
        }

        private void OnShowMultipleClicked(object sender, EventArgs e)
        {
            DemoToolIndicator.ClearAllTools();
            DemoToolIndicator.ShowTool("mistral");
            DemoToolIndicator.ShowTool("claude");
            DemoToolIndicator.ShowTool("gpt");
            DemoToolIndicator.ShowTool("web_search");
        }

        private void OnCycleToolsClicked(object sender, EventArgs e)
        {
            DemoToolIndicator.CycleThroughTools();
        }

        private void OnClearAllClicked(object sender, EventArgs e)
        {
            DemoToolIndicator.ClearAllTools();
        }
    }
}