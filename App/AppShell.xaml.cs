namespace App;

public partial class AppShell : Shell
{
	public AppShell()
	{
		InitializeComponent();
		Routing.RegisterRoute(nameof(ImageViewerPage), typeof(ImageViewerPage));
		Routing.RegisterRoute(nameof(GalleryPage), typeof(GalleryPage));
	}
}
// force rebuild