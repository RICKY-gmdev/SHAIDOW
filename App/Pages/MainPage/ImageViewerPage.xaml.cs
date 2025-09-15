namespace App;

// This attribute tells the page how to receive data from the navigation URL
[QueryProperty(nameof(ImageUrl), "ImageUrl")]
public partial class ImageViewerPage : ContentPage
{
    // This property will be automatically set by the navigation system
    public string ImageUrl
    {
        set
        {
            // When the ImageUrl is received, set the source of our Image control
            FullScreenImage.Source = ImageSource.FromUri(new Uri(value));
        }
    }

    public ImageViewerPage()
    {
        InitializeComponent();
    }
}