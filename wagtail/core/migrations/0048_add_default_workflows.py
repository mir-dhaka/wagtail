# -*- coding: utf-8 -*-
from django.db import migrations
from django.db.models import Count, Q

def create_default_workflows(apps, schema_editor):
    # Get models
    ContentType = apps.get_model('contenttypes.ContentType')
    Workflow = apps.get_model('wagtailcore.Workflow')
    GroupApprovalTask = apps.get_model('wagtailcore.GroupApprovalTask')
    GroupPagePermission = apps.get_model('wagtailcore.GroupPagePermission')
    WorkflowPage = apps.get_model('wagtailcore.WorkflowPage')
    WorkflowTask = apps.get_model('wagtailcore.WorkflowTask')
    Page = apps.get_model('wagtailcore.Page')
    Group = apps.get_model('auth.Group')

    # Create content type for GroupApprovalTask model
    group_approval_content_type, __ = ContentType.objects.get_or_create(
    model='groupapprovaltask', app_label='wagtailcore')

    publish_permissions = GroupPagePermission.objects.filter(permission_type='publish')

    for permission in publish_permissions:
        
        # find groups with publish permission over this page or its ancestors (and therefore this page by descent)
        page = permission.page
        page = Page.objects.get(pk=page.pk)
        Page.steplen = 4
        ancestors = Page.objects.ancestor_of(page)
        ancestor_permissions = moderator_permissions.filter(page__in=ancestors)
        groups = Group.objects.filter(Q(page_permissions__in=ancestor_permissions)|Q(page_permissions__pk=permission.pk)).distinct()

        # get a GroupApprovalTask with groups matching these publish permission groups (and no others)
        task = GroupApprovalTask.objects.filter(groups__id__in=groups.all()).annotate(count=Count('groups')).filter(count=groups.count()).filter(active=True).first()
        if not task:
            # if no such task exists, create it
            group_names = ' '.join([group.name for group in groups])
            task = GroupApprovalTask.objects.create(
                name=group_names+" Approval",
                content_type=group_approval_content_type,
                active=True,
            )
            task.groups.set(groups)

        # get a Workflow containing only this task if if exists, otherwise create it
        workflow = Workflow.objects.annotate(task_number=Count('workflow_tasks')).filter(task_number=1).filter(workflow_tasks__task=task).filter(active=True).first()
        if not workflow:
            workflow = Workflow.objects.create(
                name=task.name+" Workflow",
                active=True
            )

            WorkflowTask.objects.create(
                workflow=workflow,
                task=task,
                sort_order=1,
            )

        # if the workflow is not linked by a WorkflowPage to the permission's linked page, link it by creating a new WorkflowPage now
        if not WorkflowPage.objects.filter(workflow=workflow, page=page).exists():
            WorkflowPage.objects.create(
                workflow=workflow,
                page=page
            )


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0047_serialize_page_manager'),
    ]

    operations = [
        migrations.RunPython(create_default_workflows, migrations.RunPython.noop),
    ]

