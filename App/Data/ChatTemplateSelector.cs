using App.Models;
using Microsoft.Maui.Controls;

namespace App.Data
{
    public class ChatTemplateSelector : DataTemplateSelector
    {
        public DataTemplate? UserTemplate { get; set; }
        public DataTemplate? AiTemplate { get; set; }
        public DataTemplate? ImageTemplate { get; set; }

        protected override DataTemplate OnSelectTemplate(object item, BindableObject container)
        {
            if (item is not ChatMessage message)
            {
                return new DataTemplate(() => new Label { Text = "Error: Invalid message type" });
            }

            if (message.IsImage && ImageTemplate != null)
            {
                return ImageTemplate;
            }

            return message.Author == "You" ? UserTemplate : AiTemplate;
        }
    }
}