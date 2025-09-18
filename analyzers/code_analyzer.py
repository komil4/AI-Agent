import os
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from jira import JIRA
import gitlab
import requests

logger = logging.getLogger(__name__)

@dataclass
class CommitInfo:
    """Информация о коммите"""
    id: str
    message: str
    author: str
    author_email: str
    date: datetime
    files_changed: int
    lines_added: int
    lines_removed: int
    url: str

@dataclass
class ConfluencePage:
    """Информация о странице Confluence"""
    id: str
    title: str
    url: str
    author: str
    created: datetime
    updated: datetime

@dataclass
class CodeAnalysisReport:
    """Отчет по анализу кода"""
    task_key: str
    task_summary: str
    task_status: str
    task_assignee: str
    task_created: datetime
    task_updated: datetime
    
    # Коммиты
    total_commits: int
    commits: List[CommitInfo]
    first_commit_date: Optional[datetime]
    last_commit_date: Optional[datetime]
    
    # Статистика кода
    total_lines_added: int
    total_lines_removed: int
    total_files_changed: int
    
    # Авторы
    authors: List[Dict[str, Any]]
    main_author: str
    
    # Confluence страницы
    confluence_pages: List[ConfluencePage]
    
    # Временные рамки
    development_duration_days: int
    analysis_date: datetime

class CodeAnalyzer:
    def __init__(self):
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_username = os.getenv('JIRA_USERNAME')
        self.jira_token = os.getenv('JIRA_API_TOKEN')
        self.gitlab_url = os.getenv('GITLAB_URL')
        self.gitlab_token = os.getenv('GITLAB_TOKEN')
        self.confluence_url = os.getenv('ATLASSIAN_URL')
        self.confluence_username = os.getenv('ATLASSIAN_USERNAME')
        self.confluence_token = os.getenv('ATLASSIAN_API_TOKEN')
        
        self.jira = None
        self.gitlab = None
        self.confluence = None
        
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Инициализация подключений к сервисам"""
        try:
            # Jira
            if self.jira_url and self.jira_username and self.jira_token:
                self.jira = JIRA(
                    server=self.jira_url,
                    basic_auth=(self.jira_username, self.jira_token)
                )
                logger.info("✅ Подключение к Jira успешно")
            
            # GitLab
            if self.gitlab_url and self.gitlab_token:
                self.gitlab = gitlab.Gitlab(self.gitlab_url, private_token=self.gitlab_token)
                self.gitlab.auth()
                logger.info("✅ Подключение к GitLab успешно")
            
            # Confluence
            if self.confluence_url and self.confluence_username and self.confluence_token:
                from atlassian import Confluence
                self.confluence = Confluence(
                    url=self.confluence_url,
                    username=self.confluence_username,
                    password=self.confluence_token
                )
                logger.info("✅ Подключение к Confluence успешно")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации подключений: {e}")
    
    def analyze_task_code(self, task_key: str) -> Optional[CodeAnalysisReport]:
        """
        Анализирует код по задаче Jira
        """
        try:
            logger.info(f"🔍 Начинаем анализ задачи {task_key}")
            
            # Получаем информацию о задаче
            task_info = self._get_task_info(task_key)
            if not task_info:
                return None
            
            # Получаем коммиты по задаче
            commits = self._get_commits_for_task(task_key)
            
            # Получаем связанные страницы Confluence
            confluence_pages = self._get_confluence_pages_for_task(task_key)
            
            # Анализируем коммиты
            analysis = self._analyze_commits(commits)
            
            # Создаем отчет
            report = CodeAnalysisReport(
                task_key=task_key,
                task_summary=task_info['summary'],
                task_status=task_info['status'],
                task_assignee=task_info['assignee'],
                task_created=task_info['created'],
                task_updated=task_info['updated'],
                
                total_commits=len(commits),
                commits=commits,
                first_commit_date=analysis['first_commit_date'],
                last_commit_date=analysis['last_commit_date'],
                
                total_lines_added=analysis['total_lines_added'],
                total_lines_removed=analysis['total_lines_removed'],
                total_files_changed=analysis['total_files_changed'],
                
                authors=analysis['authors'],
                main_author=analysis['main_author'],
                
                confluence_pages=confluence_pages,
                
                development_duration_days=analysis['development_duration_days'],
                analysis_date=datetime.utcnow()
            )
            
            logger.info(f"✅ Анализ задачи {task_key} завершен")
            return report
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа задачи {task_key}: {e}")
            return None
    
    def _get_task_info(self, task_key: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о задаче из Jira"""
        if not self.jira:
            logger.error("Jira не подключен")
            return None
        
        try:
            issue = self.jira.issue(task_key)
            
            return {
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Не назначен',
                'created': datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z'),
                'updated': datetime.strptime(issue.fields.updated, '%Y-%m-%dT%H:%M:%S.%f%z')
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о задаче {task_key}: {e}")
            return None
    
    def _get_commits_for_task(self, task_key: str) -> List[CommitInfo]:
        """Получает коммиты связанные с задачей"""
        if not self.gitlab:
            logger.warning("GitLab не подключен")
            return []
        
        try:
            commits = []
            
            # Ищем коммиты по ключу задачи в сообщении
            search_query = f"refs {task_key}"
            projects = self.gitlab.projects.list(search=task_key, per_page=10)
            
            for project in projects:
                try:
                    # Ищем коммиты в проекте
                    project_commits = project.commits.list(
                        ref_name='main',
                        per_page=100,
                        since=(datetime.utcnow() - timedelta(days=365)).isoformat()
                    )
                    
                    for commit in project_commits:
                        if task_key.lower() in commit.message.lower():
                            commit_info = self._analyze_commit(commit, project)
                            if commit_info:
                                commits.append(commit_info)
                                
                except Exception as e:
                    logger.warning(f"Ошибка поиска коммитов в проекте {project.name}: {e}")
                    continue
            
            # Сортируем по дате
            commits.sort(key=lambda x: x.date)
            
            logger.info(f"Найдено {len(commits)} коммитов для задачи {task_key}")
            return commits
            
        except Exception as e:
            logger.error(f"Ошибка поиска коммитов: {e}")
            return []
    
    def _analyze_commit(self, commit, project) -> Optional[CommitInfo]:
        """Анализирует отдельный коммит"""
        try:
            # Получаем детали коммита
            commit_details = project.commits.get(commit.id)
            
            # Подсчитываем изменения
            stats = commit_details.stats if hasattr(commit_details, 'stats') else {}
            lines_added = stats.get('additions', 0)
            lines_removed = stats.get('deletions', 0)
            files_changed = stats.get('total', 0)
            
            return CommitInfo(
                id=commit.id,
                message=commit.message,
                author=commit.author_name,
                author_email=commit.author_email,
                date=datetime.strptime(commit.created_at, '%Y-%m-%dT%H:%M:%S.%fZ'),
                files_changed=files_changed,
                lines_added=lines_added,
                lines_removed=lines_removed,
                url=f"{project.web_url}/-/commit/{commit.id}"
            )
        except Exception as e:
            logger.warning(f"Ошибка анализа коммита {commit.id}: {e}")
            return None
    
    def _analyze_commits(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """Анализирует список коммитов"""
        if not commits:
            return {
                'first_commit_date': None,
                'last_commit_date': None,
                'total_lines_added': 0,
                'total_lines_removed': 0,
                'total_files_changed': 0,
                'authors': [],
                'main_author': 'Неизвестно',
                'development_duration_days': 0
            }
        
        # Статистика по строкам
        total_lines_added = sum(c.lines_added for c in commits)
        total_lines_removed = sum(c.lines_removed for c in commits)
        total_files_changed = sum(c.files_changed for c in commits)
        
        # Даты
        first_commit_date = min(c.date for c in commits)
        last_commit_date = max(c.date for c in commits)
        development_duration_days = (last_commit_date - first_commit_date).days
        
        # Анализ авторов
        author_stats = {}
        for commit in commits:
            author = commit.author
            if author not in author_stats:
                author_stats[author] = {
                    'name': author,
                    'commits': 0,
                    'lines_added': 0,
                    'lines_removed': 0
                }
            
            author_stats[author]['commits'] += 1
            author_stats[author]['lines_added'] += commit.lines_added
            author_stats[author]['lines_removed'] += commit.lines_removed
        
        # Сортируем авторов по количеству коммитов
        authors = sorted(author_stats.values(), key=lambda x: x['commits'], reverse=True)
        main_author = authors[0]['name'] if authors else 'Неизвестно'
        
        return {
            'first_commit_date': first_commit_date,
            'last_commit_date': last_commit_date,
            'total_lines_added': total_lines_added,
            'total_lines_removed': total_lines_removed,
            'total_files_changed': total_files_changed,
            'authors': authors,
            'main_author': main_author,
            'development_duration_days': development_duration_days
        }
    
    def _get_confluence_pages_for_task(self, task_key: str) -> List[ConfluencePage]:
        """Получает связанные страницы Confluence"""
        if not self.confluence:
            logger.warning("Confluence не подключен")
            return []
        
        try:
            pages = []
            
            # Ищем страницы по ключу задачи
            cql = f'text ~ "{task_key}"'
            search_results = self.confluence.cql(cql, limit=10)
            
            if search_results and search_results.get('results'):
                for page_data in search_results['results']:
                    try:
                        page = self.confluence.get_page_by_id(page_data['id'])
                        
                        pages.append(ConfluencePage(
                            id=page['id'],
                            title=page['title'],
                            url=f"{self.confluence_url}/pages/viewpage.action?pageId={page['id']}",
                            author=page['version']['by']['displayName'],
                            created=datetime.strptime(page['version']['when'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                            updated=datetime.strptime(page['version']['when'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        ))
                    except Exception as e:
                        logger.warning(f"Ошибка получения страницы {page_data['id']}: {e}")
                        continue
            
            logger.info(f"Найдено {len(pages)} страниц Confluence для задачи {task_key}")
            return pages
            
        except Exception as e:
            logger.error(f"Ошибка поиска страниц Confluence: {e}")
            return []
    
    def generate_report_text(self, report: CodeAnalysisReport) -> str:
        """Генерирует текстовый отчет"""
        if not report:
            return "❌ Не удалось сгенерировать отчет"
        
        # Форматируем даты
        def format_date(date):
            return date.strftime('%d.%m.%Y %H:%M') if date else 'Неизвестно'
        
        # Основная информация
        report_text = f"""
📊 **ОТЧЕТ ПО АНАЛИЗУ КОДА ЗАДАЧИ {report.task_key}**

**📋 Информация о задаче:**
• Название: {report.task_summary}
• Статус: {report.task_status}
• Исполнитель: {report.task_assignee}
• Создана: {format_date(report.task_created)}
• Обновлена: {format_date(report.task_updated)}

**💻 Статистика разработки:**
• Всего коммитов: {report.total_commits}
• Строк добавлено: {report.total_lines_added:,}
• Строк удалено: {report.total_lines_removed:,}
• Файлов изменено: {report.total_files_changed:,}
• Длительность разработки: {report.development_duration_days} дней

**👥 Авторы:**
"""
        
        # Добавляем информацию об авторах
        for i, author in enumerate(report.authors[:5], 1):
            report_text += f"• {i}. {author['name']}: {author['commits']} коммитов, +{author['lines_added']} -{author['lines_removed']} строк\n"
        
        # Временные рамки
        if report.first_commit_date and report.last_commit_date:
            report_text += f"""
**⏰ Временные рамки:**
• Первый коммит: {format_date(report.first_commit_date)}
• Последний коммит: {format_date(report.last_commit_date)}
"""
        
        # Confluence страницы
        if report.confluence_pages:
            report_text += f"""
**📄 Связанные страницы Confluence ({len(report.confluence_pages)}):**
"""
            for page in report.confluence_pages[:5]:
                report_text += f"• [{page.title}]({page.url})\n"
        
        # Коммиты
        if report.commits:
            report_text += f"""
**🔗 Последние коммиты:**
"""
            for commit in report.commits[-3:]:  # Последние 3 коммита
                report_text += f"• [{commit.id[:8]}]({commit.url}) - {commit.message[:50]}... ({format_date(commit.date)})\n"
        
        report_text += f"""
---
*Отчет сгенерирован: {format_date(report.analysis_date)}*
"""
        
        return report_text
