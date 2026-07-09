import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './gallery.component.html',
  styleUrl: './gallery.component.scss',
})
export class GalleryComponent implements OnInit {
  imageUrls = signal<string[]>([]);

  constructor(private router: Router) {}

  async ngOnInit(): Promise<void> {
    const res = await fetch('http://127.0.0.1:8000/images');
    this.imageUrls.set(res.ok ? await res.json() : []);
  }

  openImage(url: string): void {
    this.router.navigate(['/image'], { queryParams: { url } });
  }

  goBack(): void {
    this.router.navigate(['/']);
  }
}
