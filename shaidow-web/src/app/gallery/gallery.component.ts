import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './gallery.component.html',
  styleUrl: './gallery.component.scss',
})
export class GalleryComponent implements OnInit {
  imageUrls = signal<string[]>([]);

  constructor(private router: Router, private auth: AuthService) {}

  async ngOnInit(): Promise<void> {
    const res = await fetch('https://shaidow-backend-ml.azurewebsites.net/api/images',{
      headers: this.auth.authHeader(),
    });
    this.imageUrls.set(res.ok ? await res.json() : []);
  }

  openImage(url: string): void {
    this.router.navigate(['/image'], { queryParams: { url } });
  }

  goBack(): void {
    this.router.navigate(['/']);
  }
}
