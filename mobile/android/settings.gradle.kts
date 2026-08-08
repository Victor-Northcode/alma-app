// Repositories are declared here and nowhere else. `FAIL_ON_PROJECT_REPOS`
// rather than `PREFER_SETTINGS` on purpose: a module that quietly adds its own
// repository is how a build stops being reproducible, and we would rather find
// that out as an error than as a dependency resolved from somewhere unexpected.

pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "Alma"
include(":app")
