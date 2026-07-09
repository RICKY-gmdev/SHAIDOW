import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-image-viewer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './image-viewer.component.html',
  styleUrl: './image-viewer.component.scss',
})
export class ImageViewerComponent implements OnInit {
  imageUrl = signal<string>('');

  constructor(private route: ActivatedRoute, private router: Router) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => this.imageUrl.set(params['url'] ?? ''));
  }

  close(): void {
    this.router.navigate(['/gallery']);
  }

  async share(): Promise<void> {
    if (navigator.share) {
      await navigator.share({ title: 'SHAIDOW Image', url: this.imageUrl() });
    } else {
      await navigator.clipboard.writeText(this.imageUrl());
    }
  }
}
