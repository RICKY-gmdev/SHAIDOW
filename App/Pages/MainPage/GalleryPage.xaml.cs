using System.Collections.ObjectModel;

namespace App;

public partial class GalleryPage : ContentPage
{
    public ObservableCollection<string> ImageUrls { get; } = new();
    private readonly ApiService _apiService;

    public GalleryPage()
    {
        InitializeComponent();
        _apiService = new ApiService(); // Or use Dependency Injection if you set it up
        BindingContext = this;
    }
    
    protected override async void OnAppearing()
    {
        base.OnAppearing();
        await LoadImages();
    }

    private async Task LoadImages()
    {
        var urls = await _apiService.GetGeneratedImagesAsync();
        ImageUrls.Clear();
        foreach (var url in urls)
        {
            ImageUrls.Add(url);
        }
    }
    private async void OnImageSelected(object sender, SelectionChangedEventArgs e)
{
    // Get the URL of the image that was tapped
    string? selectedImageUrl = e.CurrentSelection.FirstOrDefault() as string;

    if (selectedImageUrl != null)
    {
        // Navigate to the ImageViewerPage, passing the URL as a parameter
        await Shell.Current.GoToAsync($"{nameof(ImageViewerPage)}?ImageUrl={selectedImageUrl}");

        // Deselect the item so you can tap it again
        ((CollectionView)sender).SelectedItem = null;
    }
}
}
