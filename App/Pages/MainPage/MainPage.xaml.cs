using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Net.Http;
using System.Diagnostics;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Dispatching;
using App.Models;

namespace App
{
    public partial class MainPage : ContentPage
    {
        private readonly ApiService _apiService;
        public ObservableCollection<ChatMessage> ChatMessages { get; } = new();
        private CancellationTokenSource? _cts;
        private string? _currentThreadId = null;
        private bool _isResponding = false;
        private static readonly HttpClient _httpClient = new HttpClient();


        public MainPage()
        {
            InitializeComponent();
            _apiService = new ApiService();
            ChatList.ItemsSource = ChatMessages;
            if (Application.Current != null)
            {
                Application.Current.UserAppTheme = AppTheme.Dark;
            }
        }

        

        private async Task<ImageSource?> LoadImageFromUrlAsync(string url)
        {
            try
            {
                using var httpStream = await _httpClient.GetStreamAsync(url);
                var memoryStream = new MemoryStream();
                await httpStream.CopyToAsync(memoryStream);
                memoryStream.Position = 0;
                return ImageSource.FromStream(() => memoryStream);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[ERROR] Failed to load image from stream: {ex.Message}");
                return null;
            }
        }


            private async void OnGalleryClicked(object sender, EventArgs e)
        {
            // Navigate to the GalleryPage (ensure route is registered in AppShell)
            await Shell.Current.GoToAsync(nameof(GalleryPage));
        }


        private void OnSendMessage(object sender, EventArgs e)
        {
            string userMessageText = UserInput.Text?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(userMessageText) || _isResponding) return;
            Welcome.IsVisible = false;
            var userMessage = new ChatMessage { Author = "You", Text = userMessageText };
            AddMessage(userMessage);
            UserInput.Text = string.Empty;

            _isResponding = true;
            UpdateLoadingIndicatorAnimated();
            _cts = new CancellationTokenSource();

            var aiMessagePlaceholder = new ChatMessage { Author = "SHAIDOW", Text = "..." };
            AddMessage(aiMessagePlaceholder);

            _ = Task.Run(async () =>
            {
                try
                {
                    bool firstTextChunkReceived = false;
                    string? capturedImageUrl = null;
                    bool imageBubbleWasCreated = false;
                    var toolsUsed = new List<string>();

                    await foreach (var response in _apiService.StreamChatResponseAsync(userMessageText, _currentThreadId, _cts.Token))
                    {
                        await MainThread.InvokeOnMainThreadAsync(async () =>
                        {
                            switch (response.Type)
                            {
                                case "text_chunk":
                                    if (!firstTextChunkReceived)
                                    {
                                        aiMessagePlaceholder.Text = response.Content;
                                        firstTextChunkReceived = true;
                                    }
                                    else { aiMessagePlaceholder.Text += response.Content; }
                                    break;

                                case "tool_start":
                                    ToolAnimationView.ShowTool(response.Tool ?? "default");
                                    aiMessagePlaceholder.Text = $"* (Using {response.Tool}...) *";
                                     if (response.Tool != null && !toolsUsed.Contains(response.Tool))
                                    {
                                        toolsUsed.Add(response.Tool);
                                    }
                                    break;

                                case "tool_end":
                                    ToolAnimationView.HideTool(response.Tool ?? "default");
                                    if (!string.IsNullOrEmpty(response.Output))
                                    {
                                        string outputStr = response.Output;
                                        string prefix = "IMAGE_URL::";
                                        int startIndex = outputStr.IndexOf(prefix);
                                        if (startIndex != -1)
                                        {
                                            int urlStartIndex = startIndex + prefix.Length;
                                            int urlEndIndex = outputStr.IndexOf('\'', urlStartIndex);
                                            capturedImageUrl = (urlEndIndex != -1)
                                                ? outputStr.Substring(urlStartIndex, urlEndIndex - urlStartIndex)
                                                : outputStr.Substring(urlStartIndex);
                                        }
                                    }
                                    break;

                                case "stream_end":
                                     string final_text = aiMessagePlaceholder.Text ?? "";
                            if (final_text.StartsWith("* (Using"))
                            {
                                final_text = "";
                            }
                                    if (!string.IsNullOrEmpty(capturedImageUrl))
                                    {
                                        var imageMessage = new ChatMessage
                                        {
                                            Author = "SHAIDOW",
                                            ImageUrl = capturedImageUrl,
                                            Image = await LoadImageFromUrlAsync(capturedImageUrl)
                                        };
                                        AddMessage(imageMessage);
                                        imageBubbleWasCreated = true;
                                    }
                                    if (toolsUsed.Any())
                                            {
                                                string toolsListString = "\n\n---\n*Tools Used: " + string.Join(", ", toolsUsed) + "*";
                                                final_text += toolsListString;
                                            }


                                    if (imageBubbleWasCreated && (aiMessagePlaceholder.Text != null && aiMessagePlaceholder.Text.StartsWith("* (Using")))
                                    {
                                        ChatMessages.Remove(aiMessagePlaceholder);
                                    }

                                    _currentThreadId = response.ThreadId;
                                    _isResponding = false;
                                    ToolAnimationView.ClearAllTools();
                                    UpdateLoadingIndicatorAnimated();

                                    break;

                                case "error":
                                    aiMessagePlaceholder.Text += $"\n\nSYSTEM ERROR: {response.Content}";
                                    _isResponding = false;
                                    ToolAnimationView.ClearAllTools();
                                    UpdateLoadingIndicatorAnimated();

                                    break;
                            }
                            ScrollToBottom();
                        });
                    }
                }
                catch (Exception ex)
                {
                    MainThread.BeginInvokeOnMainThread(() =>
                    {
                        aiMessagePlaceholder.Text = $"CRITICAL ERROR: {ex.Message}";
                        _isResponding = false;
                        ToolAnimationView.ClearAllTools();
                        UpdateLoadingIndicatorAnimated();

                    });
                }
            });
        }

        private void AddMessage(ChatMessage message)
        {
            ChatMessages.Add(message);
            ScrollToBottom();
        }

        private void ScrollToBottom()
        {
            if (ChatMessages.Any())
            {
                ChatList.ScrollTo(ChatMessages.Last(), position: ScrollToPosition.End, animate: true);
            }
        }

        public async void UpdateLoadingIndicatorAnimated()
        {
            if (_isResponding)
            {
                Spinner.IsVisible = true;
                Spinner.IsRunning = true;
                await Spinner.FadeTo(1, 250, Easing.SinIn);
            }
            else
            {
                await Spinner.FadeTo(0, 250, Easing.SinOut);
                Spinner.IsRunning = false;
                Spinner.IsVisible = false;
            }
        }
        // Make sure your MainPage.xaml contains: <Grid x:Name="PageContentLayout" ...>
        private void OnUserInputFocused(object sender, FocusEventArgs e)
        {
            // Note: Ensure your Input Grid in XAML is named InputContainer
            double targetWidth = PageContentLayout.Width - PageContentLayout.Padding.HorizontalThickness;
            var animation = new Animation(v => InputContainer.WidthRequest = v, InputContainer.Width, targetWidth, Easing.CubicOut);
            animation.Commit(this, "ExpandAnimation", 16, 250);
        }

        private void OnUserInputUnfocused(object sender, FocusEventArgs e)
        {
            double targetWidth = 350;
            var animation = new Animation(v => InputContainer.WidthRequest = v, InputContainer.Width, targetWidth, Easing.CubicIn);
            animation.Commit(this, "ContractAnimation", 16, 250);
        }

        private void OnLightModeClicked(object sender, EventArgs e)
        {
            if (Application.Current != null)
            {
                var newTheme = Application.Current.UserAppTheme == AppTheme.Dark ? AppTheme.Light : AppTheme.Dark;
                Application.Current.UserAppTheme = newTheme;
                UserInput.TextColor = newTheme == AppTheme.Dark ? Colors.Cyan : Colors.Black;
            }
        }
    }
}