import { Routes } from '@angular/router';
import { ChatComponent } from './chat/chat.component';
import { GalleryComponent } from './gallery/gallery.component';
import { ImageViewerComponent } from './image-viewer/image-viewer.component';
import { LoginComponent } from './login/login.component';
import { authGuard } from './auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', component: ChatComponent, canActivate: [authGuard] },
  { path: 'gallery', component: GalleryComponent, canActivate: [authGuard] },
  { path: 'image', component: ImageViewerComponent, canActivate: [authGuard] },
];