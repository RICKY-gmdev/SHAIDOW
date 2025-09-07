using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Dispatching;

namespace App
{
    public partial class ToolAnimationView : ContentView
    {
        private readonly Dictionary<string, string> _toolIcons = new()
        {
            { "mistral_tool", "mistral_icon.png" },
            { "claude_tool", "claude_icon.png" },
            { "generate_image_tool", "image_gen_icon.png" },
            { "search_for_image_tool", "search_icon.png" },
            { "default", "generic_ai_icon.png" }
        };

        private readonly List<string> _activeTools = new();
        private CancellationTokenSource? _animationCts;

        public ToolAnimationView()
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
                UpdateToolDisplay();
            }
        }

        public void HideTool(string toolName)
        {
            var normalizedTool = toolName.ToLower().Trim();
            if (_activeTools.Remove(normalizedTool))
            {
                UpdateToolDisplay();
            }
        }

        public void ClearAllTools()
        {
            if (_activeTools.Any())
            {
                _activeTools.Clear();
                UpdateToolDisplay();
            }
        }

        private void UpdateToolDisplay()
        {
            _animationCts?.Cancel();
            _animationCts = new CancellationTokenSource();
            var token = _animationCts.Token;

            IsVisible = _activeTools.Any();
            if (!IsVisible)
            {
                ToolContainerGrid.FadeTo(0);
                return;
            }

            ToolContainerGrid.FadeTo(1);

            if (_activeTools.Count == 1)
            {
                SingleToolIcon.IsVisible = true;
                MultipleToolsOrbitContainer.IsVisible = false;
                SingleToolIcon.Source = GetIconSource(_activeTools.First());
                Task.Run(async () => await AnimateSingleToolPulse(token), token);
            }
            else
            {
                SingleToolIcon.IsVisible = false;
                MultipleToolsOrbitContainer.IsVisible = true;

                var orbitIcons = new[] { OrbitIcon1, OrbitIcon2, OrbitIcon3 };
                for (int i = 0; i < orbitIcons.Length; i++)
                {
                    var icon = orbitIcons[i];
                    bool hasTool = i < _activeTools.Count;
                    icon.Source = hasTool ? GetIconSource(_activeTools[i]) : null;
                    icon.IsVisible = hasTool;
                }
                Task.Run(async () => await AnimateMultiToolOrbit(token), token);
            }
        }

        private string GetIconSource(string toolName)
        {
            foreach (var key in _toolIcons.Keys)
            {
                if (toolName.Contains(key)) return _toolIcons[key];
            }
            return _toolIcons["default"];
        }

        private async Task AnimateSingleToolPulse(CancellationToken token)
        {
            await MainThread.InvokeOnMainThreadAsync(async () =>
            {
                SingleToolIcon.Opacity = 0;
                await SingleToolIcon.FadeTo(0.8, 500);
            });
            if (token.IsCancellationRequested) return;

            while (!token.IsCancellationRequested)
            {
                await MainThread.InvokeOnMainThreadAsync(async () => await SingleToolIcon.ScaleTo(1.15, 1000, Easing.SinInOut));
                if (token.IsCancellationRequested) break;
                await MainThread.InvokeOnMainThreadAsync(async () => await SingleToolIcon.ScaleTo(1.0, 1000, Easing.SinInOut));
            }
            await MainThread.InvokeOnMainThreadAsync(async () =>
            {
                await SingleToolIcon.FadeTo(0, 250);
                SingleToolIcon.Scale = 1;
            });
        }

        private async Task AnimateMultiToolOrbit(CancellationToken token)
        {
            var orbitFrames = new[] { OrbitFrame1, OrbitFrame2, OrbitFrame3 };
            var angles = new double[] { 0, 120, 240 };
            double radius = 120;
            double rotationSpeed = 1.5;

            while (!token.IsCancellationRequested)
            {
                await MainThread.InvokeOnMainThreadAsync(() =>
                {
                    for (int i = 0; i < orbitFrames.Length; i++)
                    {
                        angles[i] = (angles[i] + rotationSpeed) % 360;
                        var angleRad = Math.PI / 180.0 * angles[i];
                        orbitFrames[i].TranslationX = radius * Math.Cos(angleRad);
                        orbitFrames[i].TranslationY = radius * Math.Sin(angleRad) * 0.7;
                    }
                });
                await Task.Delay(30, token);
            }
            await MainThread.InvokeOnMainThreadAsync(() =>
            {
                foreach (var frame in orbitFrames) { frame.TranslationX = 0; frame.TranslationY = 0; }
            });
        }
    }
}