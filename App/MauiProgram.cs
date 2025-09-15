using Microsoft.Extensions.Logging;
using CommunityToolkit.Maui;
using Microsoft.Extensions.DependencyInjection;
using System.IO;
using MauiPopup;

namespace App;

public static class MauiProgram
{
	public static MauiApp CreateMauiApp()
	{
		var builder = MauiApp.CreateBuilder();
		builder
			.UseMauiApp<App>()
			.UseMauiCommunityToolkitMediaElement() // <-- You might have this already


			.ConfigureFonts(fonts =>
			{
				fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
				fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
			});

		string dbPath = Path.Combine(FileSystem.AppDataDirectory, "ChatHistory.db3");



		builder.Services.AddSingleton<MainPage>();
		builder.Services.AddSingleton<ApiService>();
		builder.Services.AddTransient<GalleryPage>();
		builder.Services.AddTransient<ImageViewerPage>(); 

#if DEBUG
		builder.Logging.AddDebug();
#endif

		return builder.Build();
	}
}
