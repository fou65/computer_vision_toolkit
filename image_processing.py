import cv2
import numpy as np
from multiprocessing import Pool


class ImageProcessor:
    def __init__(self, filePath):
        self.filePath = filePath
        self.image = cv2.imread(self.filePath, cv2.IMREAD_ANYCOLOR)
        self.RGBhistograms, self.RGBcdf = self.get_RGB_histograms_and_cdf(self.image)
        self.image = self.convert_to_grayscale(self.image)
        self.noisy_image = None

    def get_histogram(self, image, bins_num):
        histogram = np.zeros(bins_num)
        for pixel in image:
            histogram[pixel] += 1

        return histogram

    def get_cdf(self, histogram, shape):
        if len(shape) > 1:
            no_pixels = shape[0] * shape[1]
            prob = histogram / no_pixels
        else:
            no_pixels = shape[0]
            prob = histogram / no_pixels

        cdf = np.zeros(len(prob))
        for i in range(1, len(prob)):
            cdf[i] = cdf[i - 1] + prob[i]

        return cdf

    def histogram_equalization(self, image, max_value=255):
        hist = self.get_histogram(image.flatten(), 256)
        cdf = self.get_cdf(hist, image.shape)
        normalize = np.rint(cdf * max_value).astype('int')

        result = normalize[image.flatten()]
        return result.reshape(image.shape)

    
    def image_normalization(self):
        # Ensure the image is in float format to handle division correctly
        image_float = self.image.astype(np.float32)
        # Compute the minimum and maximum pixel values
        min_val = np.min(image_float)
        max_val = np.max(image_float)
        # Normalize the image to [0, 255]
        normalized_image = ((image_float - min_val) / (max_val - min_val)) * 255
        return normalized_image.astype(np.uint8)  # Convert to uint8 for QImage


    def global_thresholding(self, threshold):
        # Create an empty image for the result
        thresholded_image = np.zeros_like(self.image)

        # Apply global thresholding
        thresholded_image[self.image >= threshold] = 255

        return thresholded_image


    def local_thresholding(self, block_size, C):
        height, width = self.image.shape
        local_thresholded_image = np.zeros((height, width), dtype=np.uint8)

        for y in range(0, height, block_size):
            for x in range(0, width, block_size):
                # Extract the current block
                block = self.image[y:y + block_size, x:x + block_size]

                # Calculate the mean intensity of the block
                block_mean = np.mean(block)

                # Apply local thresholding to the block where if condition is true (foreground) it takes white and otherwise is black
                thresholded_block = np.where(block >= (block_mean - C), 255, 0)

                # Assign the block to the result image
                local_thresholded_image[y:y + block_size, x:x + block_size] = thresholded_block

        return local_thresholded_image
    

    def add_uniform_noise(self, image, SNR):
        """
        Add uniform noise to the image.
        :param image: Input image (numpy array).
        :param SNR: Signal-to-Noise Ratio controlling the intensity of the noise.
        :return: Noisy image.
        """
        noise = np.random.uniform(low=0, high=(SNR) * 255, size=image.shape).astype(np.uint8)
        self.noisy_image = np.clip(image + noise, 0, 255).astype(np.uint8)    
        return self.noisy_image
    

    def add_gaussian_noise(self, image, sigma):
        """
        Add Gaussian noise to the image.
        :param image: Input image (numpy array).
        :param sigma: Standard deviation of the Gaussian distribution.
        :return: Noisy image.
        """
        gaussian_noise = np.random.normal(0, sigma * 255 / 5, image.shape).astype(np.uint8)
        self.noisy_image = np.clip(image + gaussian_noise, 0, 255).astype(np.uint8)
        return self.noisy_image

    
    def add_salt_and_pepper_noise(self, image, amount):
        """
        Add salt-and-pepper noise to the image.
        :param image: Input image (numpy array).
        :param amount: Probability of salt and pepper noise.
        :return: Noisy image.
        """
        self.noisy_image = np.copy(image)
        num_salt = np.ceil(amount * image.size * 0.5)
        coords = [np.random.randint(0, i - 1, int(num_salt)) for i in image.shape]
        self.noisy_image[coords[0], coords[1]] = 255

        num_pepper = np.ceil(amount * image.size * 0.5)
        coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in image.shape]
        self.noisy_image[coords[0], coords[1]] = 0
        return self.noisy_image
    







    def apply_average_filter(self, image, kernel_size=3):
        """
        Apply average filter to the image.
        :param image: Input image (numpy array).
        :param kernel_size: Size of the square kernel.
        :return: Filtered image.
        """
        pad_size = kernel_size // 2
        padded_image = np.pad(image, pad_size, mode='constant')
        
        filtered_image = np.zeros_like(image)
        
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                filtered_image[i, j] = np.mean(padded_image[i:i+kernel_size, j:j+kernel_size])
        
        return filtered_image.astype(np.uint8)

    def apply_gaussian_filter(self, image, kernel_size = 3, sigma = 10):
        """
        Apply Gaussian filter to the image.
        :param image: Input image (numpy array).
        :param kernel_size: Size of the square kernel.
        :param sigma: Standard deviation of the Gaussian distribution.
        :return: Filtered image.
        """
        kernel = np.fromfunction(lambda x, y: (1/(2*np.pi*sigma**2)) * np.exp(-((x-(kernel_size-1)//2)**2 + (y-(kernel_size-1)//2)**2) / 
                (2*sigma**2)), (kernel_size, kernel_size))
        kernel /= np.sum(kernel)

        filtered_image = self.convolve(image, kernel)      
        
        return filtered_image

    def apply_median_filter(self, image, kernel_size=3):
        """
        Apply median filter to the image.
        :param image: Input image (numpy array).
        :param kernel_size: Size of the square kernel.
        :return: Filtered image.
        """
        pad_size = kernel_size // 2
        padded_image = np.pad(image, pad_size, mode='constant')
        
        filtered_image = np.zeros_like(image)
        
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                filtered_image[i, j] = np.median(padded_image[i:i+kernel_size, j:j+kernel_size])
        
        return filtered_image.astype(np.uint8)
    





    
    def convolve(self, image, kernel):
        x, y = image.shape
        k = kernel.shape[0]
        convolved_image = np.zeros(shape=(x-2*k, y-2*k))
        for i in range(x-2*k):
            for j in range(y-2*k):
                mat = image[i:i+k, j:j+k]
                convolved_image[i, j] = np.sum(np.multiply(mat, kernel))

        return convolved_image


###########################canyy 


    def laplacian_edge(self, image, direction='both'):
        """
        Apply Laplacian edge detection to the image.
        :param image: Input image (numpy array).
        :param direction: Direction of edge detection ('x', 'y', or 'both').
        :return: Edge-detected image.
        """
        laplacian_kernel = np.array([[0, 1, 0],
                                    [1, -4, 1],
                                    [0, 1, 0]])
        return self.apply_edge(image, laplacian_kernel, direction)


    def prewitt_edge(self, image, direction='both'):
        """
        Apply Prewitt edge detection to the image.
        :param image: Input image (numpy array).
        :param direction: Direction of edge detection ('x', 'y', or 'both').
        :return: Edge-detected image.
        """
        prewitt_kernel = np.array([[-1, 0, 1],
                                    [-1, 0, 1],
                                    [-1, 0, 1]])
        return self.apply_edge(image, prewitt_kernel, direction)


    def sobel_edge(self, image, direction='both'):
        """
        Apply Sobel edge detection to the image.
        :param image: Input image (numpy array).
        :param direction: Direction of edge detection ('x', 'y', or 'both').
        :return: Edge-detected image.
        """
        sobel_kernel = np.array([[-1, 0, 1],
                                    [-2, 0, 2],
                                    [-1, 0, 1]])
        return self.apply_edge(image, sobel_kernel, direction)

    def roberts_edge(self, image, direction='both'):
        """
        Apply Roberts edge detection to the image.
        :param image: Input image (numpy array).
        :param direction: Direction of edge detection ('x', 'y', or 'both').
        :return: Edge-detected image.
        """
        roberts_kernel = np.array([[1, 0],
                                    [0, -1]])            
        return self.apply_edge(image, roberts_kernel, direction)
    

    def apply_edge(self, image, array, direction):
        if direction == 'Horizontal':
            edge = abs(self.convolve(image, array))
        elif direction == 'Vertical':
            edge = abs(self.convolve(image, array.T))
        else:
            edge_x = abs(self.convolve(image, array))
            edge_y = abs(self.convolve(image, array.T))
            edge = np.sqrt(edge_x ** 2 + edge_y ** 2)
        return edge.astype(np.uint8)


    def convert_to_grayscale(self, image):
        rgb_coefficients = [0.299, 0.587, 0.114]
        grayscale_image = np.dot(image[..., :3], rgb_coefficients)

        return grayscale_image.astype(np.uint8)


    def get_RGB_histograms_and_cdf(self, image):
        if len(image.shape) == 2:
            hist = [0] * 256
            cdf = [0] * 256
            total_pixels = image.shape[0] * image.shape[1]

            for row in image:
                for pixel in row:
                    hist[pixel] += 1

            cdf[0] = hist[0] / total_pixels
            for i in range(1, 256):
                cdf[i] = cdf[i-1] + hist[i] / total_pixels

            return [hist, hist, hist], [cdf, cdf, cdf]

        elif len(image.shape) == 3 and image.shape[2] == 3:
            hist = [[0]*256, [0]*256, [0]*256]
            cdf = [[0]*256, [0]*256, [0]*256]
            total_pixels = image.shape[0] * image.shape[1]

            for row in image:
                for pixel in row:
                    for i in range(3):
                        hist[i][pixel[i]] += 1

            for i in range(3):
                cdf[i][0] = hist[i][0] / total_pixels
                for j in range(1, 256):
                    cdf[i][j] = cdf[i][j-1] + hist[i][j] / total_pixels

            return hist, cdf
        else:
            raise ValueError("Unsupported image format")