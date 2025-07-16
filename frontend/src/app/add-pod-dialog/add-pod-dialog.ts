import { Component, Inject, Output, EventEmitter } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';

@Component({
  selector: 'app-add-pod-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatDialogModule
  ],
  templateUrl: './add-pod-dialog.html',
  styleUrls: ['./add-pod-dialog.css']
})
export class AddPodDialogComponent {
  @Output() podCreated = new EventEmitter<any>();

  newPod = {
    PodName: '',
    Resources: { gpus: 0, ram_gb: 0, storage_gb: 0 },
    image_url: '',
    machine_ip: '',
    username: '',
    password: ''
  };

  constructor(
    public dialogRef: MatDialogRef<AddPodDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {}

  createPod() {
    this.podCreated.emit({
      ...this.newPod,
      ServerName: this.data.selectedServer.id,
      Owner: this.newPod.username
    });
    this.dialogRef.close();
  }

  close() {
    this.dialogRef.close();
  }
}
