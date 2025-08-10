using Microsoft.Maui.Authentication;
using System.Diagnostics;

namespace Login_Demo;

public partial class MainPage : ContentPage
{
    public MainPage()
    {
        InitializeComponent();
    }

    private async void OnLoginClicked(object sender, EventArgs e)
    {
        try
        {
            var authResult = await WebAuthenticator.Default.AuthenticateAsync(
                new Uri("https://accounts.google.com/o/oauth2/v2/auth" +
                        "?client_id=YOUR_CLIENT_ID" +
                        "&response_type=code" +
                        "&scope=openid%20email%20profile" +
                        "&redirect_uri=com.companyname.logindemo:/oauth2redirect"),
                new Uri("com.companyname.logindemo:/oauth2redirect"));

            if (authResult.Properties.TryGetValue("code", out var code))
            {
                await DisplayAlert("Login Success", $"Auth Code: {code}", "OK");
                // TODO: Exchange 'code' for tokens via Google's OAuth token endpoint
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Login failed: {ex.Message}");
            await DisplayAlert("Login Failed", "Something went wrong. Try again.", "OK");
        }
    }
}
