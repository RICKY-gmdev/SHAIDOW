using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;
using Shaidow.Services; 
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

			.ConfigureFonts(fonts =>
			{
				fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
				fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
			});

		string dbPath = Path.Combine(FileSystem.AppDataDirectory, "ChatHistory.db3");
		builder.Services.AddSingleton(s => new ChatDatabase(dbPath));

            
        builder.Services.AddSingleton<MainPage>();
        builder.Services.AddSingleton<ApiService>();

			

#if DEBUG
		builder.Logging.AddDebug();
#endif

		return builder.Build();
	}
}
