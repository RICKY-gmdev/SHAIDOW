//

using Microsoft.Maui.ApplicationModel.DataTransfer; // <-- Add this for the Share feature
using System;

namespace App;

[QueryProperty(nameof(ImageUrl), "ImageUrl")]
public partial class ImageViewerPage : ContentPage
{
    // A private field to store the URL for the share button
    private string? _imageUrlForSharing;

    // This property is set by the navigation system
    public string ImageUrl
    {
        set
        {
            // 1. Save the URL to our private field
            _imageUrlForSharing = value;
            
            // 2. Set the source of the Image control to display the picture
            FullScreenImage.Source = ImageSource.FromUri(new Uri(value));
        }
    }

    public ImageViewerPage()
    {
        InitializeComponent();
    }

    private async void OnShareClicked(object sender, EventArgs e)
    {
        if (!string.IsNullOrEmpty(_imageUrlForSharing))
        {
            await Share.Default.RequestAsync(new ShareTextRequest
            {
                Uri = _imageUrlForSharing,
                Title = "Share AI Image",
                Text = "Check out this image created with SHAIDOW!"
            });
        }
    }

    private async void OnCloseClicked(object sender, EventArgs e)
    {
        // This correctly navigates back to the previous page (the gallery)
        await Shell.Current.GoToAsync("..");
    }
}