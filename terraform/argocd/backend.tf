terraform {
  backend "local" {
    # Файл стану буде зберігатися прямо в поточній папці
    path = "terraform.tfstate"
  }
}
