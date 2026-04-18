import { Body, Controller, Get, Post, Put, UseGuards } from '@nestjs/common';
import {
    ApiBearerAuth,
    ApiOperation,
    ApiResponse,
    ApiTags,
} from '@nestjs/swagger';
import { ZodValidationPipe } from 'src/common/pipes/zod-validation.pipe';
import { CurrentUser } from 'src/modules/auth/decorators/current-user.decorator';
import { JwtGuard } from 'src/modules/auth/guards/jwt.guard';
import { JwtPayload } from 'src/modules/auth/jwt.service';
import {
    StepOneDto,
    StepTwoDto,
    stepOneSchema,
    stepTwoSchema,
} from '../schemas/create-user.schema';
import {
    RequestEmailChangeDto,
    UpdatePasswordDto,
    UpdateUserBasicInfoDto,
    UpdateUserProfileDto,
    VerifyEmailChangeDto,
    requestEmailChangeSchema,
    updatePasswordSchema,
    updateUserBasicInfoSchema,
    updateUserProfileSchema,
    verifyEmailChangeSchema,
} from '../schemas/update-user.schema';
import { UsersService } from '../services/users.service';

@ApiTags('users')
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Post('register/step-one')
  @ApiOperation({ summary: 'User registration step one' })
  @ApiResponse({ status: 200, description: 'Step one completed successfully' })
  async stepOneRegister(
    @Body(new ZodValidationPipe(stepOneSchema)) data: StepOneDto,
  ) {
    return this.usersService.stepOneRegister(data);
  }

  @UseGuards(JwtGuard)
  @Post('register/step-two')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'User registration step two' })
  @ApiResponse({ status: 200, description: 'Profile completed successfully' })
  async stepTwoRegister(
    @Body(new ZodValidationPipe(stepTwoSchema)) data: StepTwoDto,
    @CurrentUser() currentUser: JwtPayload,
  ) {
    const result = await this.usersService.stepTwoRegister(
      currentUser.id,
      data,
    );
    return {
      message: 'Profile completed successfully',
      user: result.user,
      access_token: result.access_token,
    };
  }

  @UseGuards(JwtGuard)
  @Get('me')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get current user information' })
  @ApiResponse({
    status: 200,
    description: 'User information retrieved successfully',
  })
  async getMyInfo(@CurrentUser() currentUser: JwtPayload) {
    return await this.usersService.findById(currentUser.id);
  }

  @UseGuards(JwtGuard)
  @Get('me/profile-completion')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get current user profile completion status' })
  @ApiResponse({
    status: 200,
    description: 'Profile completion status retrieved successfully',
    schema: {
      type: 'object',
      properties: {
        isComplete: { type: 'boolean' },
        completionPercentage: { type: 'number' },
        missingFields: { type: 'array', items: { type: 'string' } },
      },
    },
  })
  async getMyProfileCompletion(@CurrentUser() currentUser: JwtPayload) {
    return await this.usersService.getProfileCompletionStatus(currentUser.id);
  }

  @UseGuards(JwtGuard)
  @Put('me')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Update current user basic information' })
  @ApiResponse({ status: 200, description: 'User updated successfully' })
  async updateMyBasicInfo(
    @Body(new ZodValidationPipe(updateUserBasicInfoSchema))
    data: UpdateUserBasicInfoDto,
    @CurrentUser() currentUser: JwtPayload,
  ) {
    const result = await this.usersService.updateUserBasicInfo(
      currentUser.id,
      data,
      currentUser,
    );
    return { user: result };
  }

  @UseGuards(JwtGuard)
  @Put('profile')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Update user profile' })
  @ApiResponse({ status: 200, description: 'Profile updated successfully' })
  async updateProfile(
    @Body(new ZodValidationPipe(updateUserProfileSchema))
    data: UpdateUserProfileDto,
    @CurrentUser() currentUser: JwtPayload,
  ) {
    const result = await this.usersService.updateUserProfile(
      currentUser.id,
      data,
    );

    if (result.roleChanged && result.updatedUser && result.access_token) {
      return {
        message: 'Profile updated successfully',
        user: result.updatedUser,
        access_token: result.access_token,
      };
    }

    return { message: 'Profile updated successfully', roleChanged: false };
  }

  @UseGuards(JwtGuard)
  @Post('me/request-email-change')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Request email change with verification code' })
  @ApiResponse({
    status: 200,
    description: 'Verification code sent successfully',
  })
  async requestEmailChange(
    @Body(new ZodValidationPipe(requestEmailChangeSchema))
    data: RequestEmailChangeDto,
    @CurrentUser() currentUser: JwtPayload,
  ) {
    return await this.usersService.requestEmailChange(currentUser.id, data);
  }

  @UseGuards(JwtGuard)
  @Post('me/verify-email-change')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Verify code and update email' })
  @ApiResponse({ status: 200, description: 'Email updated successfully' })
  async verifyEmailChange(
    @Body(new ZodValidationPipe(verifyEmailChangeSchema))
    data: VerifyEmailChangeDto,
    @CurrentUser() currentUser: JwtPayload,
  ) {
    const result = await this.usersService.verifyAndUpdateEmail(
      currentUser.id,
      data,
    );
    return { message: 'Email atualizado com sucesso', user: result };
  }

  @UseGuards(JwtGuard)
  @Put('me/password')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Update user password' })
  @ApiResponse({ status: 200, description: 'Password updated successfully' })
  async updatePassword(
    @Body(new ZodValidationPipe(updatePasswordSchema))
    data: UpdatePasswordDto,
    @CurrentUser() currentUser: JwtPayload,
  ) {
    const result = await this.usersService.updatePassword(
      currentUser.id,
      data,
    );
    return { message: 'Senha atualizada com sucesso', user: result };
  }
}
