document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("webcam");
  const canvas = document.getElementById("overlay");
  const ctx = canvas.getContext("2d");

  let selectedAccessory = null;

  // Fetch the list of accessories from the backend
  fetch("/accessories")
    .then((response) => response.json())
    .then((data) => {
      if (data.accessories && data.accessories.length > 0) {
        const accessoriesContainer = document.getElementById("accessories");
        data.accessories.forEach((accessory) => {
          const accessoryImg = document.createElement("img");
          accessoryImg.src = `${accessory}`;
          accessoryImg.alt = accessory;
          accessoryImg.title = accessory;
          accessoryImg.addEventListener("click", () => {
            selectedAccessory = accessoryImg.src;
            console.log("Selected accessory:", selectedAccessory);
          });
          accessoriesContainer.appendChild(accessoryImg);
        });
      } else {
        console.log("No accessories found.");
      }
    })
    .catch((error) => {
      console.error("Error fetching accessories:", error);
    });

  // Ensure canvas size matches video
  video.addEventListener("loadedmetadata", () => {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
  });

  // Access the webcam
  navigator.mediaDevices
    .getUserMedia({ video: true })
    .then((stream) => {
      video.srcObject = stream;
    })
    .catch((err) => {
      console.error("Error accessing webcam:", err);
    });

  // Continuous face detection function
  async function detectFaces() {
    // Clear the canvas before drawing new bounding boxes (keep the video frame)
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Flip the video horizontally by applying a scale transformation
    ctx.save();
    ctx.scale(-1, 1); // Flip horizontally
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height); // Flip the video frame
    ctx.restore();

    // Convert the current frame on canvas to an image blob
    const dataUrl = canvas.toDataURL("image/jpeg");
    const blob = await fetch(dataUrl).then((res) => res.blob());
    const formData = new FormData();
    formData.append("image", blob, "webcam.jpg");

    try {
      // Send the image to the backend for face detection
      const response = await fetch("/detect-face", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      // Debugging: Log detected faces coordinates
      console.log("Detected faces:", result.faces);

      // Always draw accessories for faces if any exist
      if (result.faces && result.faces.length > 0 && selectedAccessory) {
        result.faces.slice(0, 3).forEach(([top, right, bottom, left]) => {
          const width = right - left;
          const height = bottom - top;

          // Scale coordinates based on video size to canvas size
          const scaleX = canvas.width / video.videoWidth;
          const scaleY = canvas.height / video.videoHeight;

          const scaledLeft = left * scaleX;
          const scaledTop = top * scaleY;
          const scaledRight = right * scaleX;
          const scaledBottom = bottom * scaleY;

          const scaledWidth = scaledRight - scaledLeft;
          const scaledHeight = scaledBottom - scaledTop;

          // Draw the accessory image on top of the head
          const accessoryImg = new Image();
          accessoryImg.src = selectedAccessory;
          accessoryImg.onload = () => {
            const x = scaledLeft + (scaledWidth - scaledHeight) / 2; // Center the accessory
            const y = scaledTop - scaledHeight * 0.5; // Position above the head
            const size = scaledHeight;

            ctx.drawImage(accessoryImg, x, y, size, size); // Draw accessory image
          };
        });
      } else {
        console.log("No faces detected or no accessory selected");
      }
    } catch (error) {
      console.error("Error during face detection:", error);
    }

    // Request the next animation frame for continuous face detection
    requestAnimationFrame(detectFaces);
  }

  // Start detecting faces when the video starts playing
  video.addEventListener("playing", () => {
    console.log("Video playing. Starting face detection...");
    detectFaces(); // Start face detection once the video is playing
  });
});
