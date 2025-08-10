//MAINPAGE CODE
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Dispatching; // Required for MainThread

namespace App
{
    public partial class MainPage : ContentPage
    {
        public class ChatMessage : INotifyPropertyChanged
        {
            private string? _text;
            public string? Text
            {
                get => _text;
                set { _text = value; OnPropertyChanged(nameof(Text)); }
            }

            private string? _imageUrl;
            public string? ImageUrl
            {
                get => _imageUrl;
                set { _imageUrl = value; OnPropertyChanged(nameof(ImageUrl)); OnPropertyChanged(nameof(IsImage)); }
            }

            public bool IsText => !string.IsNullOrEmpty(Text);
            public bool IsImage => !string.IsNullOrEmpty(ImageUrl);
            public string Author { get; set; } = string.Empty;
            public LayoutOptions Alignment { get; set; } = LayoutOptions.Start;
            public Color Background { get; set; } = Colors.Transparent;

            public event PropertyChangedEventHandler? PropertyChanged;
            protected void OnPropertyChanged(string propertyName) =>
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        private readonly ApiService _apiService;
        public ObservableCollection<ChatMessage> ChatMessages { get; } = new();
        private CancellationTokenSource? _cts;

        private string? _currentThreadId = null;
        private bool _isResponding = false;

        public MainPage()
        {
            InitializeComponent();
            _apiService = new ApiService();
            ChatList.ItemsSource = ChatMessages;
            if (Application.Current != null) { Application.Current.UserAppTheme = AppTheme.Dark; }
            Preferences.Set("AppTheme", "Dark");
        }

        private async void OnSendMessage(object sender, EventArgs e)
        {
            if (_isResponding) return;

            var userMessageText = UserInput.Text?.Trim();
            if (string.IsNullOrWhiteSpace(userMessageText)) return;

            AddMessage(new ChatMessage
            {
                Author = "You",
                Text = userMessageText,
                Background = Colors.DarkCyan,
                Alignment = LayoutOptions.End
            });
            UserInput.Text = string.Empty;

            _isResponding = true;
            UpdateLoadingIndicatorAnimated();
            _cts = new CancellationTokenSource();

            _ = Task.Run(async () =>
            {
                var responseTextBuilder = new StringBuilder();
                string? finalImageUrl = null;
                string? finalToolUsed = null;

                try
                {
                    await foreach (var response in _apiService.StreamChatResponseAsync(userMessageText, _currentThreadId, _cts.Token))
                    {
                        switch (response.Type)
                        {
                            case "text_chunk":
                                responseTextBuilder.Append(response.Content);
                                break;
                            case "tool_start":
                                finalToolUsed = response.Tool;
                                break;
                            case "tool_end":
                                responseTextBuilder.Clear();
                                if (response.Output != null)
                                {
                                    if (response.Output.StartsWith("IMAGE_URL::"))
                                    {
                                        finalImageUrl = response.Output.Substring("IMAGE_URL::".Length);
                                        responseTextBuilder.Append("Here is the image you requested:");
                                    }
                                    else
                                    {
                                        responseTextBuilder.Append(response.Output);
                                    }
                                }
                                break;
                            case "stream_end":
                                _currentThreadId = response.ThreadId;
                                break;
                            case "error":
                                responseTextBuilder.Append($"\n\nSYSTEM ERROR: {response.Content}");
                                break;
                        }
                    }

                    var finalAiMessage = new ChatMessage
                    {
                        Author = "SHAIDOW",
                        Text = responseTextBuilder.ToString(),
                        ImageUrl = finalImageUrl,
                        Background = Colors.Black,
                        Alignment = LayoutOptions.Start
                    };

                    if (string.IsNullOrEmpty(finalAiMessage.Text) && string.IsNullOrEmpty(finalAiMessage.ImageUrl) && finalToolUsed != null)
                        finalAiMessage.Text = $"Task completed using {finalToolUsed}.";

                    MainThread.BeginInvokeOnMainThread(() =>
                    {
                        AddMessage(finalAiMessage);
                        _isResponding = false;
                        UpdateLoadingIndicatorAnimated();
                    });
                }
                catch (Exception ex)
                {
                    MainThread.BeginInvokeOnMainThread(() =>
                    {
                        AddMessage(new ChatMessage
                        {
                            Author = "SHAIDOW",
                            Text = $"CRITICAL ERROR: {ex.Message}",
                            Background = Colors.DarkRed,
                            Alignment = LayoutOptions.Start
                        });
                        _isResponding = false;
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

        private void OnLightModeClicked(object sender, EventArgs e)
        {
            if (Application.Current != null)
            {
                var newTheme = Application.Current.UserAppTheme == AppTheme.Dark ? AppTheme.Light : AppTheme.Dark;
                Application.Current.UserAppTheme = newTheme;
                Preferences.Set("AppTheme", newTheme == AppTheme.Dark ? "Dark" : "Light");
                UserInput.TextColor = newTheme == AppTheme.Dark ? Colors.Cyan : Colors.Black;
            }
        }

        private void ScrollToBottom()
        {
            if (ChatMessages.Any())
            {
                ChatList.ScrollTo(ChatMessages.Last(), ScrollToPosition.End, true);
            }
        }
    }
}
