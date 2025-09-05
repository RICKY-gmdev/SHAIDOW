using System.Collections.Generic;
using System.Linq;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Graphics;

namespace App
{
    public partial class ToolIndicatorView : ContentView
    {
        private readonly Dictionary<string, string> _toolIcons = new()
        {
            { "mistral", "mistral_icon.svg" },
            { "claude", "claude_icon.svg" },
            { "gpt", "gpt_icon.svg" },
            { "openai", "gpt_icon.svg" },
            { "anthropic", "claude_icon.svg" },
            { "web_search", "generic_ai_icon.svg" },
            { "file_search", "generic_ai_icon.svg" },
            { "code_generation", "generic_ai_icon.svg" },
            { "image_generation", "generic_ai_icon.svg" },
            { "default", "generic_ai_icon.svg" }
        };

        private readonly List<string> _activeTools = new();
        private bool _isAnimating = false;
        private CancellationTokenSource? _animationCts;

        public ToolIndicatorView()
        {
            InitializeComponent();
        }

        public void ShowTool(string toolName)
        {
            if (string.IsNullOrEmpty(toolName)) return;

            var normalizedTool = toolName.ToLower().Trim();
            if (!_activeTools.Contains(normalizedTool))
            {
                _activeTools.Add(normalizedTool);
                UpdateDisplay();
            }
        }

        public void HideTool(string toolName)
        {
            if (string.IsNullOrEmpty(toolName)) return;

            var normalizedTool = toolName.ToLower().Trim();
            if (_activeTools.Contains(normalizedTool))
            {
                _activeTools.Remove(normalizedTool);
                UpdateDisplay();
            }
        }

        public void ClearAllTools()
        {
            _activeTools.Clear();
            UpdateDisplay();
        }

        public void CycleThroughTools()
        {
            if (_activeTools.Count <= 1) return;

            // Rotate the tools list to show cycling effect
            var firstTool = _activeTools[0];
            _activeTools.RemoveAt(0);
            _activeTools.Add(firstTool);
            UpdateDisplay();
        }

        private void UpdateDisplay()
        {
            if (_activeTools.Count == 0)
            {
                IndicatorGrid.IsVisible = false;
                StopAnimations();
                return;
            }

            IndicatorGrid.IsVisible = true;
            StartAnimations();

            if (_activeTools.Count == 1)
            {
                ShowSingleTool();
            }
            else
            {
                ShowMultipleTools();
            }
        }

        private void ShowSingleTool()
        {
            SingleToolFrame.IsVisible = true;
            MultipleToolsGrid.IsVisible = false;

            var toolName = _activeTools.First();
            var iconSource = GetIconSource(toolName);
            SingleToolIcon.Source = iconSource;
        }

        private void ShowMultipleTools()
        {
            SingleToolFrame.IsVisible = false;
            MultipleToolsGrid.IsVisible = true;

            // Set center icon to the first tool
            var centerIconSource = GetIconSource(_activeTools.First());
            CenterIcon.Source = centerIconSource;

            // Set orbiting icons
            var orbitFrames = new[] { OrbitFrame1, OrbitFrame2, OrbitFrame3, OrbitFrame4 };
            var orbitIcons = new[] { OrbitIcon1, OrbitIcon2, OrbitIcon3, OrbitIcon4 };

            for (int i = 0; i < orbitFrames.Length && i < _activeTools.Count - 1; i++)
            {
                var toolName = _activeTools[i + 1]; // Skip first tool (center)
                var iconSource = GetIconSource(toolName);
                orbitIcons[i].Source = iconSource;
                orbitFrames[i].IsVisible = true;
            }

            // Hide unused orbit frames
            for (int i = _activeTools.Count - 1; i < orbitFrames.Length; i++)
            {
                orbitFrames[i].IsVisible = false;
            }
        }

        private string GetIconSource(string toolName)
        {
            if (_toolIcons.TryGetValue(toolName, out var icon))
            {
                return icon;
            }
            return _toolIcons["default"];
        }

        private void StartAnimations()
        {
            if (_isAnimating) return;

            _isAnimating = true;
            _animationCts = new CancellationTokenSource();

            // Start pulse animation
            _ = Task.Run(async () =>
            {
                try
                {
                    await StartPulseAnimation(_animationCts.Token);
                }
                catch (OperationCanceledException)
                {
                    // Animation was cancelled, this is expected
                }
            });

            // Start orbit animation for multiple tools
            if (MultipleToolsGrid.IsVisible)
            {
                _ = Task.Run(async () =>
                {
                    try
                    {
                        await StartOrbitAnimation(_animationCts.Token);
                    }
                    catch (OperationCanceledException)
                    {
                        // Animation was cancelled, this is expected
                    }
                });
            }

            // Start glow animation for single tool
            if (SingleToolFrame.IsVisible)
            {
                _ = Task.Run(async () =>
                {
                    try
                    {
                        await StartGlowAnimation(_animationCts.Token);
                    }
                    catch (OperationCanceledException)
                    {
                        // Animation was cancelled, this is expected
                    }
                });
            }
        }

        private void StopAnimations()
        {
            _isAnimating = false;
            _animationCts?.Cancel();
            _animationCts?.Dispose();
            _animationCts = null;
        }

        private async Task StartPulseAnimation(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested && _isAnimating)
            {
                await MainThread.InvokeOnMainThreadAsync(async () =>
                {
                    if (PulseEllipse != null)
                    {
                        // Multi-layered pulse effect
                        var pulse1 = PulseEllipse.ScaleTo(1.4, 800, Easing.SinInOut);
                        var opacity1 = PulseEllipse.FadeTo(0.3, 800, Easing.SinInOut);
                        await Task.WhenAll(pulse1, opacity1);

                        var pulse2 = PulseEllipse.ScaleTo(1.0, 800, Easing.SinInOut);
                        var opacity2 = PulseEllipse.FadeTo(0.1, 800, Easing.SinInOut);
                        await Task.WhenAll(pulse2, opacity2);

                        // Brief pause for breathing effect
                        await Task.Delay(200);
                    }
                });

                if (cancellationToken.IsCancellationRequested) break;
                await Task.Delay(100, cancellationToken);
            }
        }

        private async Task StartOrbitAnimation(CancellationToken cancellationToken)
        {
            var orbitFrames = new[] { OrbitFrame1, OrbitFrame2, OrbitFrame3, OrbitFrame4 };
            var angles = new[] { 0, 90, 180, 270 };
            var radius = 25.0;
            var rotationSpeed = 1.5; // Degrees per frame

            while (!cancellationToken.IsCancellationRequested && _isAnimating)
            {
                var tasks = new List<Task>();

                for (int i = 0; i < orbitFrames.Length; i++)
                {
                    if (cancellationToken.IsCancellationRequested) break;

                    var angle = angles[i] * Math.PI / 180;
                    var x = Math.Cos(angle) * radius;
                    var y = Math.Sin(angle) * radius;

                    // Add subtle scale variation for floating effect
                    var scale = 0.9 + 0.1 * Math.Sin(angle * 2);

                    var task = MainThread.InvokeOnMainThreadAsync(() =>
                    {
                        if (orbitFrames[i] != null && orbitFrames[i].IsVisible)
                        {
                            orbitFrames[i].TranslationX = x;
                            orbitFrames[i].TranslationY = y;
                            orbitFrames[i].Scale = scale;

                            // Add rotation for dynamic effect
                            orbitFrames[i].Rotation = angles[i];
                        }
                    });
                    tasks.Add(task);

                    // Increment angle for next frame
                    angles[i] = (int)((angles[i] + rotationSpeed) % 360);
                }

                await Task.WhenAll(tasks);
                await Task.Delay(30, cancellationToken); // Smoother animation
            }
        }

        private async Task StartGlowAnimation(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested && _isAnimating)
            {
                await MainThread.InvokeOnMainThreadAsync(async () =>
                {
                    if (SingleToolIcon != null)
                    {
                        // Breathing glow effect
                        var glow1 = SingleToolIcon.FadeTo(1.0, 600, Easing.SinInOut);
                        var scale1 = SingleToolIcon.ScaleTo(1.1, 600, Easing.SinInOut);
                        await Task.WhenAll(glow1, scale1);

                        var glow2 = SingleToolIcon.FadeTo(0.7, 600, Easing.SinInOut);
                        var scale2 = SingleToolIcon.ScaleTo(1.0, 600, Easing.SinInOut);
                        await Task.WhenAll(glow2, scale2);
                    }
                });

                if (cancellationToken.IsCancellationRequested) break;
                await Task.Delay(100, cancellationToken);
            }
        }

        protected override void OnHandlerChanged()
        {
            base.OnHandlerChanged();
            if (Handler == null)
            {
                StopAnimations();
            }
        }
    }
}