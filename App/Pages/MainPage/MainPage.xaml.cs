//MAINPAGE CODE

using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Dispatching;
using Microsoft.Maui.Storage;

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
                set { _text = value; OnPropertyChanged(nameof(Text)); OnPropertyChanged(nameof(IsText)); }
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
            BindingContext = this;
            _apiService = new ApiService();
            ChatList.ItemsSource = ChatMessages;
            if (Application.Current != null)
            {
                Application.Current.UserAppTheme = AppTheme.Dark;
            }
            Preferences.Set("AppTheme", "Dark");
        }

        private void OnUserInputFocused(object sender, FocusEventArgs e)
        {
            double targetWidth = PageContentLayout.Width - PageContentLayout.Padding.HorizontalThickness;
            var animation = new Animation(
                v => InputContainer.WidthRequest = v,
                InputContainer.Width,
                targetWidth,
                Easing.CubicOut
            );
            animation.Commit(this, "ExpandAnimation", 16, 250);
        }

        private void OnUserInputUnfocused(object sender, FocusEventArgs e)
        {
            double targetWidth = 350;
            var animation = new Animation(
                v => InputContainer.WidthRequest = v,
                InputContainer.Width,
                targetWidth,
                Easing.CubicIn
            );
            animation.Commit(this, "ContractAnimation", 16, 250);
        }



        private void OnSendMessage(object sender, EventArgs e)
        {
            string userMessageText = UserInput.Text?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(userMessageText) || _isResponding)
            {

                return;
            }

            var userMessage = new ChatMessage
            {
                Author = "You",
                Text = userMessageText,
                Background = Colors.DarkCyan,
                Alignment = LayoutOptions.End
            };
            AddMessage(userMessage);
            UserInput.Text = string.Empty;

            _isResponding = true;
            UpdateLoadingIndicatorAnimated();
            _cts = new CancellationTokenSource();

            var aiMessage = new ChatMessage
            {
                Author = "SHAIDOW",
                Text = "",
                Background = Colors.Black,
                Alignment = LayoutOptions.Start
            };
            AddMessage(aiMessage);

            _ = Task.Run(async () =>
            {
                try
                {
                    bool firstTextChunkReceived = false;
                    await foreach (var response in _apiService.StreamChatResponseAsync(userMessageText, _currentThreadId, _cts.Token))
                    {
                        MainThread.BeginInvokeOnMainThread(() =>
                        {
                            switch (response.Type)
                            {
                                case "text_chunk":
                                    if (!firstTextChunkReceived)
                                    {
                                        aiMessage.Text = response.Content;
                                        firstTextChunkReceived = true;
                                    }
                                    else
                                    {
                                        aiMessage.Text += response.Content;
                                    }
                                    ScrollToBottom();
                                    break;

                                case "tool_start":
                                    ToolAnimationView.ShowTool(response.Tool ?? "default");
                                    aiMessage.Text = $"* (Using {response.Tool}...) *";
                                    ScrollToBottom();
                                    break;

                                case "tool_end":
                                    ToolAnimationView.HideTool(response.Tool ?? "default");
                                    if (response.Output != null && (response.Output.StartsWith("IMAGE_URL::") || response.Output.StartsWith("IMAGE_DATA::")))
                                    {
                                        aiMessage.ImageUrl = response.Output.Replace("IMAGE_URL::", "").Replace("IMAGE_DATA::", "");
                                    }
                                    ScrollToBottom();
                                    break;

                                case "stream_end":
                                    _currentThreadId = response.ThreadId;
                                    _isResponding = false;
                                    ToolAnimationView.ClearAllTools();
                                    UpdateLoadingIndicatorAnimated();
                                    break;

                                case "error":
                                    aiMessage.Text += $"\n\nSYSTEM ERROR: {response.Content}";
                                    _isResponding = false;
                                    ToolAnimationView.ClearAllTools();
                                    UpdateLoadingIndicatorAnimated();
                                    break;
                            }
                        });
                    }
                }
                catch (Exception ex)
                {
                    MainThread.BeginInvokeOnMainThread(() =>
                    {
                        aiMessage.Text = $"CRITICAL ERROR: {ex.Message}";
                        aiMessage.Background = Colors.DarkRed;
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

        private void ReplaceMessage(ChatMessage oldMessage, ChatMessage newMessage)
        {
            var index = ChatMessages.IndexOf(oldMessage);
            if (index != -1)
            {
                ChatMessages[index] = newMessage;
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