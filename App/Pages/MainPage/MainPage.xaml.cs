using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Text;
using Microsoft.Maui.Controls;

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

            public bool IsText =>!string.IsNullOrEmpty(Text);
            public bool IsImage =>!string.IsNullOrEmpty(ImageUrl);
            public string Author { get; set; } = string.Empty;
            public LayoutOptions Alignment { get; set; } = LayoutOptions.Start;
            public Color Background { get; set; } = Colors.Transparent;

            public event PropertyChangedEventHandler? PropertyChanged;
            protected void OnPropertyChanged(string propertyName) =>
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        private readonly ApiService _apiService;
        public ObservableCollection<ChatMessage> ChatMessages { get; } = new();

        
        private string? _currentThreadId = null;
        private bool _isResponding = false;

        public MainPage()
        {
            InitializeComponent();
            _apiService = new ApiService();
            ChatList.ItemsSource = ChatMessages;
            if (Application.Current!= null) { Application.Current.UserAppTheme = AppTheme.Dark; }
            Preferences.Set("AppTheme", "Dark");
        }

        private async void OnSendMessage(object sender, EventArgs e)
        {
            if (_isResponding) return;
            var userMessageText = UserInput.Text?.Trim();
            if (string.IsNullOrWhiteSpace(userMessageText)) return;

            // Add user's message to the UI
            AddMessage(new ChatMessage { Author = "You", Text = userMessageText, Background = Colors.DarkCyan, Alignment = LayoutOptions.End });
            UserInput.Text = string.Empty;

            _isResponding = true;
            UpdateLoadingIndicatorAnimated();

            // Create a placeholder message for the AI's response that will be populated by the stream
            var aiMessage = new ChatMessage { Author = "SHAIDOW", Text = "", Background = Colors.Black, Alignment = LayoutOptions.Start };
            AddMessage(aiMessage);

            try
            {
                // Await foreach over the stream of events from the API service
                await foreach (var response in _apiService.StreamChatResponseAsync(userMessageText, _currentThreadId))
                {
                    // All UI updates must be run on the main thread
                    MainThread.BeginInvokeOnMainThread(() =>
                    {
                        switch (response.type)
                        {
                            case "text_chunk":
                                // Append text chunks to the AI message content for a typing effect
                                aiMessage.Text += response.content;
                                break;

                            case "tool_start":
                                // Show the user that the agent is using a tool
                                aiMessage.Text += $"\n*SHAIDOW is using {response.tool}...*";
                                break;

                            case "tool_end":
                                // Handle the output from the tool, specifically for images
                                if (response.output!= null && response.output.StartsWith("Image generated successfully:"))
                                {
                                    var imageUrl = response.output.Replace("Image generated successfully:", "").Trim();
                                    aiMessage.ImageUrl = imageUrl;
                                    aiMessage.Text = "Here is the image you requested:"; // Update text to accompany the image
                                }
                                break;

                            case "stream_end":
                                // The agent has finished its turn. Save the thread_id for the next message.
                                _currentThreadId = response.thread_id;
                                break;

                            case "error":
                                aiMessage.Text += $"\n\nSYSTEM ERROR: {response.content}";
                                break;
                        }
                    });
                }
            }
            catch (Exception ex)
            {
                MainThread.BeginInvokeOnMainThread(() =>
                {
                    aiMessage.Text += $"\n\nCRITICAL ERROR: {ex.Message}";
                });
            }
            finally
            {
                _isResponding = false;
                UpdateLoadingIndicatorAnimated();
            }
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
            if (Application.Current!= null)
            {
                var newTheme = Application.Current.UserAppTheme == AppTheme.Dark? AppTheme.Light : AppTheme.Dark;
                Application.Current.UserAppTheme = newTheme;
                Preferences.Set("AppTheme", newTheme == AppTheme.Dark? "Dark" : "Light");
                UserInput.TextColor = newTheme == AppTheme.Dark? Colors.Cyan : Colors.Black;
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