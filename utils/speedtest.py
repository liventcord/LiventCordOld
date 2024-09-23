import requests
import time

# URL of Flask app's file hosting endpoint
url = 'http://localhost:5005/download-windows'
domain = 'https://liventcord.loophole.site/download-windows'

def run_speed_test(url, chunk_size=1024, interval=1):
    start_time = time.time()
    response = requests.get(url, stream=True)
    # Initialize variables for calculating transfer rate
    total_bytes_read = 0
    start_interval = start_time
    
    for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:
            total_bytes_read += len(chunk)
            
            # Calculate elapsed time for the current interval
            elapsed_interval = time.time() - start_interval
            
            if elapsed_interval >= interval:
                # Calculate transfer rate in MB/s for the current interval
                transfer_rate_MBps = (total_bytes_read / 1024 / 1024) / elapsed_interval
                print(f'Transfer Rate for {url}: {transfer_rate_MBps:.2f} MB/s')
                
                # Reset interval variables
                total_bytes_read = 0
                start_interval = time.time()
    
    end_time = time.time()
    return response.status_code, (end_time - start_time)

if __name__ == '__main__':
    # Adjust chunk size to control download speed (e.g., chunk_size=2048 for slower speed)
    status_code, response_time = run_speed_test(url, chunk_size=1024)
    print(f'Status Code to localhost: {status_code}')
    print(f'Total Response Time to localhost: {response_time} seconds')
    
    status_code, response_time = run_speed_test(domain, chunk_size=1024)
    print(f'Status Code to public domain: {status_code}')
    print(f'Total Response Time to public domain: {response_time} seconds')
