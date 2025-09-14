using System.Globalization;
using Markdig;
using Microsoft.Maui.Controls;
namespace App.Converters
{
    public class MarkdownToHtmlConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is not string markdownText) return string.Empty;
            return Markdown.ToHtml(markdownText ?? "");
        }
        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}