# Vercel — Next.js Frontend

resource "vercel_project" "frontend" {
  name      = var.project_name
  framework = "nextjs"

  git_repository = {
    type = "github"
    repo = var.github_repo
  }

  root_directory = "web"

  environment = [
    {
      key    = "CORE_API_URL"
      value  = "http://${aws_eip.backend.public_ip}"
      target = ["production", "preview"]
    },
  ]
}
