import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

const TOOL_ICONS: Record<string, string> = {
  mistral_tool: '🧠',
  reasoning_tool: '🧩',
  coding_tool: '💻',
  generate_image_tool: '🎨',
  search_for_image_tool: '🔍',
  default: '✨',
};

@Component({
  selector: 'app-tool-animation',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tool-animation.component.html',
  styleUrl: './tool-animation.component.scss',
})
export class ToolAnimationComponent {
  private activeTools = signal<string[]>([]);

  isVisible = computed(() => this.activeTools().length > 0);
  isSingle = computed(() => this.activeTools().length === 1);
  tools = computed(() => this.activeTools());

  iconFor(tool: string): string {
    const normalized = tool.toLowerCase().trim();
    const match = Object.keys(TOOL_ICONS).find((key) => normalized.includes(key));
    return TOOL_ICONS[match ?? 'default'];
  }

  showTool(toolName: string): void {
    const normalized = toolName.toLowerCase().trim();
    if (!this.activeTools().includes(normalized)) {
      this.activeTools.update((tools) => [...tools, normalized]);
    }
  }

  hideTool(toolName: string): void {
    const normalized = toolName.toLowerCase().trim();
    this.activeTools.update((tools) => tools.filter((t) => t !== normalized));
  }

  clearAll(): void {
    this.activeTools.set([]);
  }
}
