from locust import HttpUser, task, between

class ShortenerUser(HttpUser):
    wait_time = between(1, 5)
    
    @task
    def create_link(self):
        self.client.post("/links/shorten", json={
            "original_url": "https://example.com"
        })
    
    @task(3)
    def redirect_link(self):
        self.client.get("/testalias", allow_redirects=False)
    
    @task(2)
    def view_stats(self):
        self.client.get("/links/testalias/stats")
    
    def on_start(self):
        # Логин перед выполнением задач
        response = self.client.post("/login", json={
            "email": "test@example.com",
            "password": "secret"  # Должен совпадать с паролем в фикстурах
        })
        if response.status_code != 200:
            self.environment.runner.quit()
