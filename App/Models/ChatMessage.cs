using System.ComponentModel;
namespace App.Models
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
        public event PropertyChangedEventHandler? PropertyChanged;
        protected void OnPropertyChanged(string propertyName) =>
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}